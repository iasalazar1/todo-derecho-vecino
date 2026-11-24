"""Handler HTTP de AWS Lambda para Todo Derecho Vecino."""

import base64
import json
import logging
import os

import boto3

from generar_respuesta import answer_question
from retriever import (
    is_general_table_22_question,
    is_land_use_compatibility_question,
    retrieve,
    retrieve_hybrid,
    MissingStructuredParameters,
    StructuredRetrievalError,
    Table22NoRecords,
)

# Estados de respuesta controlada que indican que no hubo evidencia
# estructurada o que faltan datos estructurados para obtenerla, y que, por
# tanto, no fueron derivados al modelo generativo.
ESTADOS_CONTROLADOS_ESTRUCTURA = {
    "structured_retrieval_error",
    "table_22_no_matches",
    "missing_structured_parameters",
}

# Contrato HTTP: código por estado de respuesta.
# - answered / table_22_no_matches / missing_structured_parameters: 200
#   (el estado exacto viaja en el campo `status` del cuerpo JSON).
# - structured_retrieval_error: 503 (fallo técnico de la recuperación
#   estructurada; nunca debe presentarse como respuesta jurídica).
CODIGOS_HTTP_POR_ESTADO = {
    "answered": 200,
    "table_22_no_matches": 200,
    "missing_structured_parameters": 200,
    "structured_retrieval_error": 503,
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Se reutiliza el cliente durante la vida del entorno de ejecución Lambda.
_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client

    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
        )

    return _bedrock_client


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
        },
        "isBase64Encoded": False,
        "body": json.dumps(payload, ensure_ascii=False),
    }

def _parse_request(event):
    """Parsea el evento HTTP y extrae question, top_k, activity, zonification.

    Returns (question, top_k, activity, zonification).

    Raises ValueError con mensaje descriptivo si los parámetros son inválidos.
    """
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Cuerpo JSON inválido o ausente.")

    question = body.get("question")
    top_k = body.get("top_k", 5)
    activity = body.get("activity")
    zonification = body.get("zonification")

    # Validación: question es obligatorio
    if not question:
        raise ValueError("El campo question es obligatorio.")

    # Validación: top_k debe ser entero entre 1 y 10
    if not isinstance(top_k, int) or not (1 <= top_k <= 10):
        raise ValueError("top_k debe estar entre 1 y 10.")

    # Validación: activity y zonification deben venir juntas o ninguna
    if (activity is not None) != (zonification is not None):
        if activity is not None:
            raise ValueError(
                "Si se proporciona activity, también debe proporcionarse zonification."
            )
        else:
            raise ValueError(
                "Si se proporciona zonification, también debe proporcionarse activity."
            )

    return question, top_k, activity, zonification


def lambda_handler(event, context):
    """Handler principal de Lambda.

    Decide automáticamente si usar retrieve() o retrieve_hybrid() según
    si se proporcionen activity y zonification.

    Returns dict con la respuesta HTTP formateada.
    """
    # 1. Parsear y validar parámetros
    question, top_k, activity, zonification = _parse_request(event)

    # 2. Obtener cliente Bedrock
    bedrock_client = _get_bedrock_client()

    # 3. Selección de escenario de recuperación:
    # - Escenario B: activity y zonification explícitas -> consulta estructurada puntual.
    # - Escenario C: pregunta general sobre Tabla 22 (detectada vía
    #   is_general_table_22_question importada de retriever, no vía globals()).
    # - Enrutamiento obligatorio: pregunta de compatibilidad/permiso/prohibición
    #   de uso de suelo del PPCU Hipódromo sin parámetros estructurados -> estado
    #   controlado `missing_structured_parameters` (HTTP 200) que solicita
    #   únicamente los datos faltantes. NO cae en recuperación semántica ni
    #   invoca al modelo; no se infieren actividad ni zonificación.
    # - Escenario A: recuperación semántica habitual.
    # La detección solo participa cuando no hay parámetros estructurados;
    # nunca infiere estados, actividades ni zonificaciones.
    if activity is not None and zonification is not None:
        escenario = "B_estructurada"
    elif is_general_table_22_question(question):
        escenario = "C_tabla_22_general"
    elif is_land_use_compatibility_question(question):
        logger.info(
            "Consulta de compatibilidad de uso de suelo sin parámetros "
            "estructurados: se solicitan los datos faltantes."
        )
        return _response(200, {
            "status": "missing_structured_parameters",
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "missing_fields": ["activity", "zonification"],
            "limitations": [
                "La pregunta requiere consultar la evidencia estructurada de "
                "la Tabla 22 de usos de suelo del PPCU Hipódromo, pero no se "
                "proporcionaron la actividad y la zonificación a evaluar.",
                "Reenvíe la consulta incluyendo en el cuerpo JSON el campo "
                "'activity' (nombre de la actividad) y el campo "
                "'zonification' (una de: H, HC, HO, HM, HCS, E, EA).",
                "No se generó ninguna conclusión jurídica ni se infirió la "
                "compatibilidad solicitada.",
            ],
            "model_id": None,
        })
    else:
        escenario = "A_semantica"

    logger.info("Escenario de recuperación seleccionado: %s", escenario)

    if escenario in ("B_estructurada", "C_tabla_22_general"):
        # Path híbrido: retrieve_hybrid ejecuta semántica + ruta estructurada
        # correspondiente (B puntual o C general de Tabla 22).
        def lambda_retrieve(q, top_k=5):
            return retrieve_hybrid(
                question=q,
                top_k=top_k,
                activity=activity,
                zonification=zonification,
                connection_mode="aurora",
                secret_arn=os.environ.get("DB_SECRET_ARN", ""),
                region_name=AWS_REGION,
                client=bedrock_client,
            )
    else:
        # Path semántico: retrieve simple
        def lambda_retrieve(q, top_k=5):
            return retrieve(
                question=q,
                top_k=top_k,
                connection_mode="aurora",
                secret_arn=os.environ.get("DB_SECRET_ARN", ""),
                region_name=AWS_REGION,
                client=bedrock_client,
            )

    # 4. Llamar a answer_question con el wrapper inyectado.
    # answer_question reconoce StructuredRetrievalError, Table22NoRecords y
    # MissingStructuredParameters y devuelve resultados controlados; se repite
    # aquí la captura como red de seguridad para que el fallo nunca derive en
    # 500 sin cuerpo controlado.
    try:
        result = answer_question(
            question=question,
            top_k=top_k,
            retriever_fn=lambda_retrieve,
            bedrock_client=bedrock_client,
            region_name=AWS_REGION,
        )
    except (StructuredRetrievalError, Table22NoRecords, MissingStructuredParameters) as exc:
        logger.error("Recuperación estructurada no disponible: %s", exc)
        if isinstance(exc, StructuredRetrievalError):
            estado = "structured_retrieval_error"
        elif isinstance(exc, Table22NoRecords):
            estado = "table_22_no_matches"
        else:
            estado = "missing_structured_parameters"
        result = {
            "status": estado,
            "question": question.strip(),
            "answer": "",
            "citations": [],
            "missing_fields": getattr(exc, "missing_fields", []),
            "limitations": [
                str(exc),
                (
                    "No se generó una conclusión jurídica sustitutiva; la "
                    "evidencia semántica no reemplaza la evidencia "
                    "estructurada de Tabla 22."
                ),
            ],
            "model_id": None,
        }

    if result.get("status") in ESTADOS_CONTROLADOS_ESTRUCTURA:
        logger.info(
            "Respuesta controlada por falta de evidencia estructurada: %s",
            result.get("status"),
        )

    # 5. Retornar respuesta formateada con el código HTTP del contrato.
    status_code = CODIGOS_HTTP_POR_ESTADO.get(
        result.get("status"), 200
    )
    return _response(status_code, result)
