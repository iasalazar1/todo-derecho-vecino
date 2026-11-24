
"""Recuperación semántica de fragmentos legales desde Aurora PostgreSQL."""

import argparse
import json
import os
import logging
import re
import unicodedata

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

    try:
        response = secrets_client.get_secret_value(
            SecretId=secret_arn
        )
    except RuntimeError:
        raise
    except Exception as exc:
        # Errores del SDK (ClientError, EndpointConnectionError, etc.) o de
        # cualquier cliente inyectado en pruebas: fallo técnico explícito.
        # El detalle completo queda en la cadena de excepción para los logs,
        # sin exponer el contenido del secreto.
        raise RuntimeError(
            "No fue posible obtener el secreto de Aurora desde Secrets "
            f"Manager (tipo de error: {type(exc).__name__})."
        ) from exc

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


def _execute_aurora_query(sql, parameters, credentials):
    """Ejecuta una consulta parametrizada en Aurora y devuelve la primera fila.

    Los errores de psycopg (conexión, SQL, ejecución) se convierten en
    RuntimeError con un diagnóstico del tipo de error: el detalle original
    queda en la cadena de excepción para los logs, sin exponer credenciales
    ni contenido del secreto.
    """

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "No está instalado psycopg. Instala psycopg[binary]."
        ) from exc

    try:
        with psycopg.connect(
            **credentials,
            sslmode="require",
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                return cursor.fetchone()
    except psycopg.Error as exc:
        raise RuntimeError(
            "Error de PostgreSQL al ejecutar la consulta en Aurora "
            f"(tipo de error: {type(exc).__name__})."
        ) from exc


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

    row = _execute_aurora_query(sql, parameters, credentials)

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


def _build_land_use_sql(mode):
    """Construye la consulta SQL de la Tabla 22 según el modo de conexión."""
    if mode == "local":
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
    elif mode == "aurora":
        sql = """
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
        WHERE documento_id = %(documento_id)s
          AND tabla_id = %(tabla_id)s
          AND zonificacion = %(zonification)s
          AND (
              LOWER(actividad_original) = LOWER(%(activity)s)
              OR EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(alias_busqueda) AS a(alias)
                  WHERE LOWER(a.alias) = LOWER(%(activity)s)
              )
          )
        ORDER BY actividad_id
    ) AS result;
    """
    else:
        raise ValueError("Modo de conexión no válido.")

    return sql


def _retrieve_land_use_local(
    activity,
    zonification,
    host,
    port,
    database,
    username,
):
    """Ejecuta la consulta de la Tabla 22 mediante psql y PGPASSFILE."""

    pgpassfile = os.environ.get("PGPASSFILE")

    if not pgpassfile or not os.path.isfile(pgpassfile):
        raise RuntimeError(
            "Define PGPASSFILE con la ruta al archivo de credenciales "
            "de PostgreSQL antes de consultar la Tabla 22."
        )

    sql = _build_land_use_sql("local")

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


def _retrieve_land_use_aurora(
    activity,
    zonification,
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Ejecuta la consulta de la Tabla 22 directamente contra Aurora mediante psycopg."""

    credentials = _get_aurora_credentials(
        secret_arn=secret_arn,
        secrets_client=secrets_client,
        region_name=region_name,
    )

    sql = _build_land_use_sql("aurora")

    parameters = {
        "documento_id": "ppdu_hipodromo",
        "tabla_id": "tabla_22",
        "zonification": zonification,
        "activity": activity.strip(),
    }

    row = _execute_aurora_query(sql, parameters, credentials)

    if not row or not row[0]:
        return []

    result = row[0]

    if isinstance(result, str):
        return json.loads(result)

    return result


def retrieve_land_use(
    activity,
    zonification,
    host="127.0.0.1",
    port=15432,
    database="tododerechovecino",
    username="tdv_admin",
    connection_mode="local",
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Busca una actividad y zonificación en la Tabla 22 de Hipódromo.

    connection_mode:
        local  -> psql, PGPASSFILE y túnel SSM en puerto 15432.
        aurora -> psycopg, Secrets Manager y conexión SSL a Aurora.
    """

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

    if connection_mode == "local":
        return _retrieve_land_use_local(
            activity=activity,
            zonification=zonification,
            host=host,
            port=port,
            database=database,
            username=username,
        )

    if connection_mode == "aurora":
        return _retrieve_land_use_aurora(
            activity=activity,
            zonification=zonification,
            secret_arn=secret_arn,
            secrets_client=secrets_client,
            region_name=region_name,
        )

    raise ValueError(
        "connection_mode debe ser 'local' o 'aurora'."
    )


logger = logging.getLogger(__name__)

VALID_ZONIFICATIONS = {"H", "HC", "HO", "HM", "HCS", "E", "EA"}

HIPPODROMO_DOCUMENTO_ID = "ppdu_hipodromo"
HIPODROMO_TABLA_ID = "tabla_22"
GENERAL_TABLE22_TIPO_EVIDENCIA = "structured_table_summary"


class StructuredRetrievalError(RuntimeError):
    """Fallo técnico de la recuperación estructurada de Tabla 22.

    Se lanza cuando la consulta a land_use_compatibility falla por conexión,
    SQL, credenciales o credenciales/secretos ausentes. Indica que no fue
    posible consultar la evidencia estructurada necesaria; la evidencia
    semántica NO debe usarse como sustituto.
    """


class Table22NoRecords(Exception):
    """La consulta estructurada de Tabla 22 se ejecutó sin coincidencias.

    No es un error técnico: la consulta funcionó y no encontró registros
    (actividad/alias ausentes en modo puntual o tabla vacía en modo general).
    Impide responder como si hubiera evidencia estructurada y evita inferir
    que una actividad está permitida o prohibida.
    """


class MissingStructuredParameters(Exception):
    """Consulta de compatibilidad de uso de suelo sin datos estructurados.

    La consulta requiere la evidencia estructurada de Tabla 22, pero no se
    dispuso de actividad y zonificación explícitas (p. ej., el frontend solo
    envió `question`). No se infieren valores ni se degrada a recuperación
    semántica: el llamador debe solicitar únicamente los datos faltantes
    listados en `missing_fields`.
    """

    def __init__(self, message, missing_fields=None):
        super().__init__(message)
        self.missing_fields = list(missing_fields or [])


def _strip_accents(text):
    """Normaliza texto a minúsculas y sin acentos para detección robusta."""

    normalized = unicodedata.normalize("NFD", text.lower())
    return unicodedata.normalize(
        "NFC",
        "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn"),
    )


GENERAL_TABLE22_PHRASES = (
    ("tabla", "usos de suelo"),
    ("tabla", "usos del suelo"),
    ("tabla de usos",),
    ("tabla", "compatibilidad"),
    ("tabla 22",),
)

GENERAL_TABLE22_PROGRAM_REFS = (
    "hipodromo",
    "ppdu",
    "ppcu",
    "programa parcial",
)

# Frases que indican consulta puntual de una actividad (no consulta general
# de la tabla): piden permiso/prohibición de algo concreto.
TABLE22_SPECIFIC_PATTERNS = (
    r"es permitid[oa]",
    r"esta permitid[oa]",
    r"se permite",
    r"es prohibid[oa]",
    r"esta prohibid[oa]",
    r"puedo poner",
    r"puedo abrir",
    r"puedo instalar",
    r"puede abrir",
    r"puedo establecer",
    r"donde (puedo|puede)",
)

TABLE22_ZONIFICATION_TOKEN = re.compile(
    r"\b(h|hc|ho|hm|hcs|e|ea)\b",
)


def is_general_table_22_question(question):
    """Detecta preguntas generales sobre la Tabla 22 del PPCU Hipódromo.

    Reglas de detección (conservadoras):
    - Requiere mención explícita de la tabla ("tabla", "tabla de usos",
      "tabla de compatibilidad" o "tabla 22") junto con una referencia al
      Programa Parcial de Hipódromo ("hipodromo", "ppdu", "ppcu" o
      "programa parcial"); o mención directa de "tabla 22".
    - NO es general si la pregunta menciona una zonificación puntual
      (token H, HC, HO, HM, HCS, E o EA como palabra aislada) o formula una
      consulta específica de permiso/prohibición de una actividad
      ("¿es permitido...?", "¿puedo poner...?"), para no confundir una
      pregunta puntual con una consulta general.
    - La detección solo decide enrutamiento; nunca infiere estados.
    """

    if not isinstance(question, str):
        return False

    normalized = _strip_accents(question)

    mentions_table = any(
        all(phrase in normalized for phrase in phrases)
        for phrases in GENERAL_TABLE22_PHRASES
    )
    if not mentions_table:
        return False

    mentions_program = any(
        ref in normalized for ref in GENERAL_TABLE22_PROGRAM_REFS
    )
    if not mentions_program:
        return False

    # Consulta puntual de permiso/prohibición de una actividad concreta.
    for pattern in TABLE22_SPECIFIC_PATTERNS:
        if re.search(pattern, normalized):
            return False

    # Consulta que menciona una zonificación puntual (H, HC, ...).
    if TABLE22_ZONIFICATION_TOKEN.search(normalized):
        return False

    return True


# Patrones de intención de compatibilidad de uso de suelo: piden saber si
# una actividad (concreta o implícita) está permitida o prohibida, o qué
# uso de suelo aplica. Se combinan con una referencia al PPCU Hipódromo
# para activar la ruta estructurada; una mención de Hipódromo sola NO
# activa nada (consultas jurídicas generales siguen siendo semánticas).
# Se aplican sobre texto normalizado sin acentos.
LAND_USE_COMPATIBILITY_PATTERNS = (
    # Permiso / prohibición explícita de una actividad
    r"\bpuedo (abrir|poner|instalar|establecer|mantener|operar|montar|habilitar)\b",
    r"\bpuede (abrir|poner|instalar|establecer|operar)\b",
    r"\bes permitid[oa]s?\b",
    r"\besta permitid[oa]s?\b",
    r"\bse permite\b",
    r"\bes prohibid[oa]s?\b",
    r"\besta prohibid[oa]s?\b",
    r"\bse prohibe\b",
    # Uso de suelo permitido o prohibido, con o sin actividad explícita
    r"\busos? de suelo\b.{0,40}\b(permitid|prohibid)",
    r"\bque usos? de suelo\b",
    # Compatibilidad de uso de suelo
    r"\bcompatibilidad de (uso|usos)\b",
)


def is_land_use_compatibility_question(question):
    """Detecta consultas de compatibilidad de uso de suelo del PPCU Hipódromo.

    Reglas de detección (conservadoras):
    - Precedencia: si la pregunta ya es una consulta general de Tabla 22
      (is_general_table_22_question), retorna False; el escenario C la atiende
      y esa detección tiene prioridad.
    - Requiere DOS condiciones simultáneas: intención de compatibilidad
      (patrón de permiso, prohibición o utilizable en LAND_USE_COMPATIBILITY_
      PATTERNS) y referencia al PPCU Hipódromo ("hipodromo", "ppdu", "ppcu"
      o "programa parcial"). Una mención de Hipódromo sin intención de
      compatibilidad NO activa la ruta estructurada (permanece semántica, A).
      Una intención de compatibilidad sin referencia al programa tampoco.
    - Solo decide enrutamiento; nunca infiere actividad, zonificación ni
      estados.
    """
    if not isinstance(question, str):
        return False

    # Precedencia del escenario C.
    if is_general_table_22_question(question):
        return False

    normalized = _strip_accents(question)

    mentions_program = any(
        ref in normalized for ref in GENERAL_TABLE22_PROGRAM_REFS
    )
    if not mentions_program:
        return False

    for pattern in LAND_USE_COMPATIBILITY_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return False


def _build_table_22_general_sql(mode):
    """Construye la consulta general de Tabla 22 según el modo de conexión.

    Genera un registro resumen por actividad donde CADA zonificación conserva
    su propia procedencia (estado literal, fuente, páginas, marca de
    revisión y, si existiera en los datos, nota), mediante jsonb_agg de
    objetos. No se usan MAX()/MIN() para seleccionar una fuente o página
    común a todos los estados. Sin exigir actividad ni zonificación,
    filtrado exclusivamente por documento_id y tabla_id.
    """

    if mode == "local":
        sql = r"""
    SELECT COALESCE(json_agg(row_to_json(result)), '[]'::json)::text
    FROM (
        SELECT
            actividad_id,
            MAX(actividad_original) AS actividad,
            MAX(categoria) AS categoria,
            MAX(subcategoria) AS subcategoria,
            jsonb_agg(
                jsonb_build_object(
                    'zonificacion', zonificacion,
                    'estado_original', estado_original,
                    'fuente_archivo', fuente_archivo,
                    'fuente_paginas', fuente_paginas,
                    'needs_review', needs_review
                ) ORDER BY zonificacion
            ) AS estados_por_zonificacion,
            BOOL_OR(needs_review) AS pendiente_revision
        FROM land_use_compatibility
        WHERE documento_id = :'documento_id'
          AND tabla_id = :'tabla_id'
        GROUP BY actividad_id
        ORDER BY actividad_id
    ) AS result;
    """
    elif mode == "aurora":
        sql = """
    SELECT COALESCE(json_agg(row_to_json(result)), '[]'::json)::text
    FROM (
        SELECT
            actividad_id,
            MAX(actividad_original) AS actividad,
            MAX(categoria) AS categoria,
            MAX(subcategoria) AS subcategoria,
            jsonb_agg(
                jsonb_build_object(
                    'zonificacion', zonificacion,
                    'estado_original', estado_original,
                    'fuente_archivo', fuente_archivo,
                    'fuente_paginas', fuente_paginas,
                    'needs_review', needs_review
                ) ORDER BY zonificacion
            ) AS estados_por_zonificacion,
            BOOL_OR(needs_review) AS pendiente_revision
        FROM land_use_compatibility
        WHERE documento_id = %(documento_id)s
          AND tabla_id = %(tabla_id)s
        GROUP BY actividad_id
        ORDER BY actividad_id
    ) AS result;
    """
    else:
        raise ValueError("Modo de conexión no válido.")

    return sql


def _retrieve_table_22_general_local(
    host,
    port,
    database,
    username,
):
    """Ejecuta la consulta general de Tabla 22 mediante psql y PGPASSFILE."""

    pgpassfile = os.environ.get("PGPASSFILE")

    if not pgpassfile or not os.path.isfile(pgpassfile):
        raise RuntimeError(
            "Define PGPASSFILE con la ruta al archivo de credenciales "
            "de PostgreSQL antes de consultar la Tabla 22."
        )

    sql = _build_table_22_general_sql("local")

    command = [
        "psql", "-X", "-w", "-A", "-t", "-q",
        "-h", host,
        "-p", str(port),
        "-U", username,
        "-d", database,
        "-v", "ON_ERROR_STOP=1",
        "-v", f"documento_id={HIPPODROMO_DOCUMENTO_ID}",
        "-v", f"tabla_id={HIPODROMO_TABLA_ID}",
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
            "Falló la consulta general de Tabla 22. "
            f"Detalle de PostgreSQL: {result.stderr.strip()}"
        )

    output = result.stdout.strip()

    if not output:
        return []

    return json.loads(output)


def _retrieve_table_22_general_aurora(
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Ejecuta la consulta general de Tabla 22 contra Aurora mediante psycopg."""

    credentials = _get_aurora_credentials(
        secret_arn=secret_arn,
        secrets_client=secrets_client,
        region_name=region_name,
    )

    sql = _build_table_22_general_sql("aurora")

    parameters = {
        "documento_id": HIPPODROMO_DOCUMENTO_ID,
        "tabla_id": HIPODROMO_TABLA_ID,
    }

    row = _execute_aurora_query(sql, parameters, credentials)

    if not row or not row[0]:
        return []

    result = row[0]

    if isinstance(result, str):
        return json.loads(result)

    return result


def retrieve_table_22_general(
    host="127.0.0.1",
    port=15432,
    database="tododerechovecino",
    username="tdv_admin",
    connection_mode="local",
    secret_arn=None,
    secrets_client=None,
    region_name="us-east-1",
):
    """Recupera la Tabla 22 del PPCU Hipódromo sin actividad ni zonificación.

    Devuelve un registro resumen por actividad con:
        actividad_id, actividad, categoria, subcategoria,
        estados_por_zonificacion (lista de objetos, uno por zonificación,
        cada uno con zonificacion, estado_original, fuente_archivo,
        fuente_paginas y needs_review propios),
        pendiente_revision (verdadero si alguna celda lo está).

    No infere estados ni procedencia: cada valor se devuelve literalmente
    tal como está en land_use_compatibility. Las notas de Tabla 22 no
    existen hoy como columna estructurada; si un registro individual
    llegara a incluir 'nota', se conserva tal cual (ver generar_respuesta).
    """

    if connection_mode == "local":
        raw_rows = _retrieve_table_22_general_local(
            host=host,
            port=port,
            database=database,
            username=username,
        )
    elif connection_mode == "aurora":
        raw_rows = _retrieve_table_22_general_aurora(
            secret_arn=secret_arn,
            secrets_client=secrets_client,
            region_name=region_name,
        )
    else:
        raise ValueError(
            "connection_mode debe ser 'local' o 'aurora'."
        )

    normalized_rows = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        entry = dict(row)
        entry.setdefault("documento_id", HIPPODROMO_DOCUMENTO_ID)
        entry.setdefault("tabla_id", HIPODROMO_TABLA_ID)
        entry["tipo_evidencia"] = GENERAL_TABLE22_TIPO_EVIDENCIA
        normalized_rows.append(entry)

    normalized_rows.sort(key=lambda x: str(x.get("actividad_id", "")))

    return normalized_rows




def _is_valid_structured_request(activity, zonification):
    """Determina si activity y zonification cumplen los criterios estrictos para consulta estructurada."""
    if not isinstance(activity, str) or not activity.strip():
        return False
    if not isinstance(zonification, str) or not zonification.strip():
        return False
    if zonification.strip().upper() not in VALID_ZONIFICATIONS:
        return False
    return True


def retrieve_hybrid(
    question,
    activity=None,
    zonification=None,
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
    """Recuperación híbrida: combina búsqueda semántica amplia y consulta estructurada de Tabla 22.

    Reglas de enrutamiento:
    - Ejecuta siempre recuperación semántica vía `retrieve()`. Los errores en esta ruta se propagan.
    - Escenario B: si `activity` y `zonification` son explícitos y válidos, ejecuta la consulta
      estructurada vía `retrieve_land_use()`. No infiere parámetros a partir del texto de la
      pregunta. Un fallo técnico (conexión, SQL, credenciales) lanza `StructuredRetrievalError`;
      una consulta sin coincidencias lanza `Table22NoRecords`: no se continúa con la evidencia
      semántica como sustituto y no se infiere que la actividad esté permitida o prohibida.
    - Escenario C: si no hay parámetros estructurados y `is_general_table_22_question(question)`
      detecta una pregunta general sobre Tabla 22, ejecuta `retrieve_table_22_general()`, que
      recupera un resumen por actividad de `documento_id='ppdu_hipodromo'` y `tabla_id='tabla_22'`,
      sin exigir actividad ni zonificación y sin inferir estados. Un fallo técnico lanza
      `StructuredRetrievalError`; una tabla sin registros lanza `Table22NoRecords`. En ambos casos
      no se continúa con evidencia semántica como sustituto de la evidencia estructurada.
    - Enrutamiento obligatorio: si la pregunta es de compatibilidad/permiso/prohibición de uso
      de suelo del PPCU Hipódromo (is_land_use_compatibility_question) y no hay parámetros
      estructurados, se lanza `MissingStructuredParameters` ANTES de ejecutar cualquier
      recuperación: la consulta no se envía a recuperación semántica ni se invoca al modelo.
      No se infieren actividad ni zonificación; el llamador debe solicitar los datos faltantes
      listados en `missing_fields`.
    - Escenario A: preguntas sin relación estructurada conservan el comportamiento semántico
      habitual, sin exigir Tabla 22.
    """
    # 0. Enrutamiento obligatorio para consultas de compatibilidad de uso de
    #    suelo sin parámetros estructurados (p. ej., el frontend solo envía
    #    `question`): la evidencia semántica NO es sustituto de Tabla 22.
    if (
        not _is_valid_structured_request(activity, zonification)
        and not is_general_table_22_question(question)
        and is_land_use_compatibility_question(question)
    ):
        raise MissingStructuredParameters(
            "La consulta requiere la evidencia estructurada de Tabla 22 "
            "(usos de suelo del PPCU Hipódromo), pero no se proporcionaron "
            "la actividad y la zonificación a evaluar. No se infieren los "
            "valores faltantes: reenvíe la consulta con los parámetros "
            "estructurados.",
            missing_fields=["activity", "zonification"],
        )

    # 1. Recuperación semántica obligatoria
    semantic_results = retrieve(
        question=question,
        top_k=top_k,
        host=host,
        port=port,
        database=database,
        username=username,
        client=client,
        connection_mode=connection_mode,
        secret_arn=secret_arn,
        secrets_client=secrets_client,
        region_name=region_name,
    )

    # Normalizar resultados semánticos con tipo_evidencia y deduplicar
    normalized_semantics = []
    seen_semantic_keys = set()
    for item in semantic_results:
        key = (
            item.get("documento"),
            item.get("articulo"),
            item.get("segmento"),
        )
        if key in seen_semantic_keys:
            continue
        seen_semantic_keys.add(key)
        entry = dict(item)
        entry["tipo_evidencia"] = "semantic_chunk"
        normalized_semantics.append(entry)

    # 2. Escenario B: recuperación estructurada puntual (actividad + zonificación)
    structured_results = []
    if _is_valid_structured_request(activity, zonification):
        try:
            raw_structured = retrieve_land_use(
                activity=activity.strip(),
                zonification=zonification.strip().upper(),
                host=host,
                port=port,
                database=database,
                username=username,
                connection_mode=connection_mode,
                secret_arn=secret_arn,
                secrets_client=secrets_client,
                region_name=region_name,
            )
        except (StructuredRetrievalError, Table22NoRecords):
            raise
        except Exception as exc:
            # Fallo técnico (conexión, SQL, psycopg, credenciales/secretos o
            # cualquier error de ejecución que impida recuperar Tabla 22):
            # la evidencia semántica no es sustituto de la estructurada; se
            # propaga un error tipado para respuesta controlada. La cadena
            # (raise ... from_exc) conserva el diagnóstico para los logs
            # sin exponer credenciales.
            raise StructuredRetrievalError(
                "No fue posible consultar la evidencia estructurada de "
                "Tabla 22 (PPCU Hipódromo): la consulta a la base de datos "
                f"falló ({type(exc).__name__})."
            ) from exc

        if not raw_structured:
            # Consulta ejecutada correctamente sin coincidencias: no es error
            # técnico, pero tampoco evidencia. Se impide inferir estado.
            raise Table22NoRecords(
                "La consulta estructurada se ejecutó correctamente pero no "
                "encontró coincidencias en la Tabla 22 para la actividad y "
                "zonificación indicadas. No puede concluirse que la "
                "actividad esté permitida ni prohibida."
            )

        seen_structured_keys = set()
        for row in raw_structured:
            key = (row.get("actividad_id"), row.get("zonificacion"))
            if key in seen_structured_keys:
                continue
            seen_structured_keys.add(key)
            entry = dict(row)
            entry["tipo_evidencia"] = "structured_row"
            entry.setdefault("documento", "Programa Parcial de Desarrollo Urbano Hipódromo")
            entry.setdefault("documento_id", "ppdu_hipodromo")
            entry.setdefault("tabla_id", "tabla_22")
            structured_results.append(entry)

    # 3. Escenario C: pregunta general sobre Tabla 22, sin exigir actividad ni zonificación
    general_table_results = []
    if not _is_valid_structured_request(activity, zonification):
        if is_general_table_22_question(question):
            try:
                raw_general = retrieve_table_22_general(
                    host=host,
                    port=port,
                    database=database,
                    username=username,
                    connection_mode=connection_mode,
                    secret_arn=secret_arn,
                    secrets_client=secrets_client,
                    region_name=region_name,
                )
            except (StructuredRetrievalError, Table22NoRecords):
                raise
            except Exception as exc:
                # Fallo técnico: no se entrega la respuesta semántica como
                # sustituto de la evidencia estructurada requerida.
                raise StructuredRetrievalError(
                    "No fue posible consultar la evidencia estructurada de "
                    "Tabla 22 (PPCU Hipódromo): la consulta general a la "
                    f"base de datos falló ({type(exc).__name__})."
                ) from exc

            if not raw_general:
                # Consulta sin registros: sin evidencia estructurada que
                # sustente una conclusión de compatibilidad.
                raise Table22NoRecords(
                    "La consulta general de Tabla 22 se ejecutó "
                    "correctamente pero no devolvió registros. No puede "
                    "presentarse una conclusión sobre compatibilidad de "
                    "usos de suelo."
                )

            seen_general_keys = set()
            for row in raw_general:
                key = row.get("actividad_id")
                if key in seen_general_keys:
                    continue
                seen_general_keys.add(key)
                entry = dict(row)
                entry.setdefault(
                    "documento", "Programa Parcial de Desarrollo Urbano Hipódromo"
                )
                entry.setdefault("documento_id", "ppdu_hipodromo")
                entry.setdefault("tabla_id", "tabla_22")
                general_table_results.append(entry)

    # Ordenamiento determinista por actividad_id ascendente
    structured_results.sort(key=lambda x: str(x.get("actividad_id", "")))
    general_table_results.sort(key=lambda x: str(x.get("actividad_id", "")))

    # Fusión determinista: structured_row (B) primero, resumen general de Tabla 22 (C)
    # después y semantic_chunk (A) al final.
    return structured_results + general_table_results + normalized_semantics



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
