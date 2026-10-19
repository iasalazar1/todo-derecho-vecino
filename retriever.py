"""Recuperación semántica de fragmentos legales desde Aurora PostgreSQL."""

import argparse
import json
import os
import subprocess

import boto3

from generar_embeddings import generate_embedding, DIMENSIONS


def retrieve(
    question,
    top_k=5,
    host="127.0.0.1",
    port=15432,
    database="tododerechovecino",
    username="tdv_admin",
    client=None,
):
    """Devuelve los fragmentos más similares a una pregunta."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k debe ser un entero positivo.")

    pgpassfile = os.environ.get("PGPASSFILE")
    if not pgpassfile or not os.path.isfile(pgpassfile):
        raise RuntimeError(
            "Define PGPASSFILE con la ruta al archivo de credenciales "
            "de PostgreSQL antes de ejecutar el retriever."
        )

    if client is None:
        client = boto3.client("bedrock-runtime", region_name="us-east-1")

    vector = generate_embedding(client, question)
    if len(vector) != DIMENSIONS:
        raise ValueError(f"Se esperaban {DIMENSIONS} dimensiones.")

    vector_sql = "[" + ",".join(str(float(x)) for x in vector) + "]"

    sql = """
    WITH candidatos AS (
        SELECT
            d.name AS documento,
            c.article AS articulo,
            c.legal_citation AS cita_legal,
            (e.embedding <=> :'vector'::vector) AS distancia,
            e.segment_index AS segmento,
            e.needs_review AS pendiente_revision,
            LEFT(e.segment_text, 1500) AS fragmento,
            ts_rank_cd(
                to_tsvector('spanish', COALESCE(e.segment_text, '')),
                plainto_tsquery('spanish', :'question')
            ) AS relevancia_textual
        FROM legal_embeddings e
        JOIN legal_documents d ON d.id = e.document_id
        JOIN legal_chunks c
          ON c.id = e.legal_chunk_id
         AND c.document_id = e.document_id
        ORDER BY e.embedding <=> :'vector'::vector
        LIMIT :candidate_k
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
        LIMIT :top_k
    ) AS result;
    """

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
        description="Recuperación semántica y consulta estructurada de información legal."
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Pregunta jurídica para la búsqueda semántica."
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--activity",
        help="Nombre de la actividad para consultar la Tabla 22."
    )
    parser.add_argument(
        "--zonification",
        help="Clave de zonificación: H, HC, HO, HM, HCS, E o EA."
    )

    args = parser.parse_args()

    # Consulta estructurada de la Tabla 22
    if args.activity is not None or args.zonification is not None:
        if not args.activity or not args.zonification:
            parser.error(
                "--activity y --zonification deben utilizarse juntos."
            )

        resultados = retrieve_land_use(
            args.activity,
            args.zonification
        )

    # Búsqueda semántica existente
    else:
        if not args.question:
            parser.error(
                "Indica una pregunta jurídica o utiliza "
                "--activity junto con --zonification."
            )

        resultados = retrieve(
            args.question,
            top_k=args.top_k
        )

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    print(f"\nResultados recuperados: {len(resultados)}")

if __name__ == "__main__":
    main()
