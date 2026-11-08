
"""Recuperación semántica de fragmentos legales desde Aurora PostgreSQL."""

import argparse
import json
import os
import subprocess

import boto3

from generar_embeddings import generate_embedding, DIMENSIONS


def _build_retrieval_sql(mode):
    """Construye la consulta híbrida para psql o psycopg."""

    sql = """
    WITH candidatos AS (
        SELECT
            d.name AS documento,
            c.article AS articulo,
            c.legal_citation AS cita_legal,
            (e.embedding <=> VECTOR_PARAM) AS distancia,
            e.segment_index AS segmento,
            e.needs_review AS pendiente_revision,
            LEFT(e.segment_text, 1500) AS fragmento,
            ts_rank_cd(
                to_tsvector('spanish', COALESCE(e.segment_text, '')),
                plainto_tsquery('spanish', QUESTION_PARAM)
            ) AS relevancia_textual
        FROM legal_embeddings e
        JOIN legal_documents d ON d.id = e.document_id
        JOIN legal_chunks c
          ON c.id = e.legal_chunk_id
         AND c.document_id = e.document_id
        ORDER BY e.embedding <=> VECTOR_PARAM
        LIMIT CANDIDATE_K_PARAM
    ),
    resultados AS (
        SELECT
            *,
            distancia - LEAST(relevancia_textual, 1.0) * 0.08
                AS puntuacion_hibrida
        FROM candidatos
    )
    SELECT COALESCE(json_agg(row_to_json(result)), '[]'::json)::text
    FROM (
        SELECT
            documento,
            articulo,
            cita_legal,
            ROUND(distancia::numeric, 6) AS distancia_coseno,
            segmento,
            pendiente_revision,
            fragmento
        FROM resultados
        ORDER BY puntuacion_hibrida ASC, distancia ASC
        LIMIT TOP_K_PARAM
    ) AS result;
    """

    if mode == "local":
        replacements = {
            "VECTOR_PARAM": ":'vector'::vector",
            "QUESTION_PARAM": ":'question'",
            "CANDIDATE_K_PARAM": ":candidate_k",
            "TOP_K_PARAM": ":top_k",
        }
    elif mode == "aurora":
        replacements = {
            "VECTOR_PARAM": "%(vector)s::vector",
            "QUESTION_PARAM": "%(question)s",
            "CANDIDATE_K_PARAM": "%(candidate_k)s",
            "TOP_K_PARAM": "%(top_k)s",
        }
    else:
        raise ValueError("Modo de conexión no válido.")

    for placeholder, replacement in replacements.items():
        sql = sql.replace(placeholder, replacement)

    return sql


def _get_aurora_credentials(
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Obtiene las credenciales de Aurora desde AWS Secrets Manager."""

    secret_arn = secret_arn or os.environ.get("DB_SECRET_ARN")

    if not secret_arn:
        raise RuntimeError(
            "Falta DB_SECRET_ARN: define el ARN del secreto de Aurora."
        )

    if secrets_client is None:
        secrets_client = boto3.client(
            "secretsmanager",
            region_name=region_name,
        )

    response = secrets_client.get_secret_value(
        SecretId=secret_arn
    )

    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError(
            "El secreto de Aurora no contiene SecretString."
        )

    try:
        secret = json.loads(secret_string)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "El contenido del secreto de Aurora no es JSON válido."
        ) from exc

    if not isinstance(secret, dict):
        raise RuntimeError(
            "El secreto de Aurora debe contener un objeto JSON."
        )

    credentials = {
        "host": (
            secret.get("host")
            or os.environ.get("DB_HOST")
        ),
        "port": (
            secret.get("port")
            or os.environ.get("DB_PORT")
            or 5432
        ),
        "dbname": (
            secret.get("dbname")
            or secret.get("database")
            or os.environ.get("DB_NAME")
        ),
        "user": secret.get("username") or secret.get("user"),
        "password": secret.get("password"),
    }

    missing = [
        key for key, value in credentials.items()
        if value is None or value == ""
    ]

    if missing:
        raise RuntimeError(
            "Faltan campos obligatorios en el secreto de Aurora: "
            + ", ".join(missing)
        )

    try:
        credentials["port"] = int(credentials["port"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "El puerto definido en el secreto de Aurora no es válido."
        ) from exc

    return credentials


def _retrieve_local(
    question,
    top_k,
    vector_sql,
    host,
    port,
    database,
    username,
):
    """Ejecuta la consulta mediante psql y PGPASSFILE."""

    pgpassfile = os.environ.get("PGPASSFILE")

    if not pgpassfile or not os.path.isfile(pgpassfile):
        raise RuntimeError(
            "Define PGPASSFILE con la ruta al archivo de credenciales "
            "de PostgreSQL antes de ejecutar el retriever."
        )

    sql = _build_retrieval_sql("local")

    entrada_psql = (
        f"\\set vector '{vector_sql}'\n"
        f"\\set top_k {top_k}\n"
        f"\\set candidate_k {top_k * 4}\n"
        + sql
    )

    comando = [
        "psql", "-X", "-w", "-A", "-t", "-q",
        "-h", host,
        "-p", str(port),
        "-U", username,
        "-d", database,
        "-v", f"question={question}",
        "-v", "ON_ERROR_STOP=1",
    ]

    resultado = subprocess.run(
        comando,
        input=entrada_psql,
        capture_output=True,
        text=True,
        check=False,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "Falló la consulta al retriever. "
            f"Detalle de PostgreSQL: {resultado.stderr.strip()}"
        )

    salida = resultado.stdout.strip()

    if not salida:
        return []

    return json.loads(salida)


def _retrieve_aurora(
    question,
    top_k,
    vector_sql,
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Ejecuta la consulta directamente contra Aurora mediante psycopg."""

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "No está instalado psycopg. Instala psycopg[binary]."
        ) from exc

    credentials = _get_aurora_credentials(
        secret_arn=secret_arn,
        secrets_client=secrets_client,
        region_name=region_name,
    )

    sql = _build_retrieval_sql("aurora")

    parameters = {
        "vector": vector_sql,
        "question": question,
        "candidate_k": top_k * 4,
        "top_k": top_k,
    }

    with psycopg.connect(
        **credentials,
        sslmode="require",
        connect_timeout=5,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            row = cursor.fetchone()

    if not row or not row[0]:
        return []

    result = row[0]

    if isinstance(result, str):
        return json.loads(result)

    return result


def retrieve(
    question,
    top_k=5,
    host="127.0.0.1",
    port=15432,
    database="tododerechovecino",
    username="tdv_admin",
    client=None,
    connection_mode="local",
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """
    Devuelve los fragmentos legales más similares a una pregunta.

    connection_mode:
        local  -> psql, PGPASSFILE y túnel SSM en puerto 15432.
        aurora -> psycopg, Secrets Manager y conexión SSL a Aurora.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k debe ser un entero positivo.")

    if connection_mode not in {"local", "aurora"}:
        raise ValueError(
            "connection_mode debe ser 'local' o 'aurora'."
        )

    if client is None:
        client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
        )

    vector = generate_embedding(client, question)

    if len(vector) != DIMENSIONS:
        raise ValueError(
            f"Se esperaban {DIMENSIONS} dimensiones."
        )

    vector_sql = "[" + ",".join(
        str(float(x)) for x in vector
    ) + "]"

    if connection_mode == "local":
        return _retrieve_local(
            question=question,
            top_k=top_k,
            vector_sql=vector_sql,
            host=host,
            port=port,
            database=database,
            username=username,
        )

    return _retrieve_aurora(
        question=question,
        top_k=top_k,
        vector_sql=vector_sql,
        secret_arn=secret_arn,
        secrets_client=secrets_client,
        region_name=region_name,
    )


def retrieve_land_use(
    activity,
    zonification,
    host="127.0.0.1",
    port=15432,
    database="tododerechovecino",
    username="tdv_admin",
):
    """Busca una actividad y zonificación en la Tabla 22 de Hipódromo."""

    if not isinstance(activity, str) or not activity.strip():
        raise ValueError("La actividad no puede estar vacía.")

    if not isinstance(zonification, str):
        raise ValueError("La zonificación debe ser texto.")

    zonification = zonification.strip().upper()
    valid_zonifications = {"H", "HC", "HO", "HM", "HCS", "E", "EA"}

    if zonification not in valid_zonifications:
        raise ValueError(
            f"Zonificación no válida: {zonification}. "
            f"Valores admitidos: {', '.join(sorted(valid_zonifications))}."
        )

    pgpassfile = os.environ.get("PGPASSFILE")

    if not pgpassfile or not os.path.isfile(pgpassfile):
        raise RuntimeError(
            "Define PGPASSFILE con la ruta al archivo de credenciales "
            "de PostgreSQL antes de consultar la Tabla 22."
        )

    sql = r"""
    SELECT COALESCE(json_agg(row_to_json(result)), '[]'::json)::text
    FROM (
        SELECT
            actividad_id,
            actividad_original AS actividad,
            categoria,
            subcategoria,
            zonificacion,
            estado_original,
            fuente_archivo,
            fuente_paginas,
            needs_review AS pendiente_revision
        FROM land_use_compatibility
        WHERE documento_id = 'ppdu_hipodromo'
          AND tabla_id = 'tabla_22'
          AND zonificacion = :'zonification'
          AND (
              LOWER(actividad_original) = LOWER(:'activity')
              OR EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(alias_busqueda) AS a(alias)
                  WHERE LOWER(a.alias) = LOWER(:'activity')
              )
          )
        ORDER BY actividad_id
    ) AS result;
    """

    command = [
        "psql", "-X", "-w", "-A", "-t", "-q",
        "-h", host,
        "-p", str(port),
        "-U", username,
        "-d", database,
        "-v", "ON_ERROR_STOP=1",
        "-v", f"activity={activity.strip()}",
        "-v", f"zonification={zonification}",
    ]

    result = subprocess.run(
        command,
        input=sql,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Falló la consulta estructurada. "
            f"Detalle de PostgreSQL: {result.stderr.strip()}"
        )

    output = result.stdout.strip()

    if not output:
        return []

    return json.loads(output)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recuperación semántica y consulta estructurada "
            "de información legal."
        )
    )

    parser.add_argument(
        "question",
        nargs="?",
        help="Pregunta jurídica para la búsqueda semántica.",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--activity",
        help="Nombre de la actividad para consultar la Tabla 22.",
    )
    parser.add_argument(
        "--zonification",
        help="Clave de zonificación: H, HC, HO, HM, HCS, E o EA.",
    )

    args = parser.parse_args()

    if args.activity is not None or args.zonification is not None:
        if not args.activity or not args.zonification:
            parser.error(
                "--activity y --zonification deben utilizarse juntos."
            )

        resultados = retrieve_land_use(
            args.activity,
            args.zonification,
        )
    else:
        if not args.question:
            parser.error(
                "Indica una pregunta jurídica o utiliza "
                "--activity junto con --zonification."
            )

        resultados = retrieve(
            args.question,
            top_k=args.top_k,
        )

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    print(f"\nResultados recuperados: {len(resultados)}")


if __name__ == "__main__":
    main()
