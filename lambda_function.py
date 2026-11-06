"""Handler HTTP de AWS Lambda para Todo Derecho Vecino."""

import base64
import json
import logging
import os

import boto3

from generar_respuesta import answer_question
from retriever import retrieve


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
    """Valida y extrae los datos de una petición HTTP API Gateway."""

    if not isinstance(event, dict):
        raise ValueError("La petición no tiene un formato válido.")

    method = (
        event.get("requestContext", {})
        .get("http", {})
        .get("method")
    )

    if method and method.upper() != "POST":
        raise PermissionError("Método HTTP no permitido.")

    body = event.get("body")

    if not isinstance(body, str) or not body.strip():
        raise ValueError("El cuerpo de la petición está vacío.")

    if event.get("isBase64Encoded", False):
        try:
            body = base64.b64decode(body, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("El cuerpo codificado no es válido.") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("El cuerpo debe contener JSON válido.") from exc

    if not isinstance(data, dict):
        raise ValueError("El JSON debe ser un objeto.")

    question = data.get("question")
    top_k = data.get("top_k", 5)

    if not isinstance(question, str) or not question.strip():
        raise ValueError("El campo question es obligatorio.")

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k debe ser un número entero.")

    if not 1 <= top_k <= 10:
        raise ValueError("top_k debe estar entre 1 y 10.")

    return question.strip(), top_k


def lambda_handler(event, context):
    """Procesa una consulta jurídica recibida mediante API Gateway."""

    try:
        question, top_k = _parse_request(event)

    except PermissionError as exc:
        return _response(405, {
            "status": "error",
            "message": str(exc),
        })

    except ValueError as exc:
        return _response(400, {
            "status": "error",
            "message": str(exc),
        })

    try:
        bedrock_client = _get_bedrock_client()

        # El recuperador utiliza Aurora directamente, sin túnel SSM.
        def lambda_retrieve(question, top_k=5):
            return retrieve(
                question=question,
                top_k=top_k,
                connection_mode="aurora",
                client=bedrock_client,
                secret_arn=os.environ.get("DB_SECRET_ARN"),
                region_name=AWS_REGION,
            )

        result = answer_question(
            question=question,
            top_k=top_k,
            retriever_fn=lambda_retrieve,
            bedrock_client=bedrock_client,
            region_name=AWS_REGION,
        )

        request_id = getattr(context, "aws_request_id", "local-test")

        logger.info(
            "Consulta procesada. request_id=%s status=%s",
            request_id,
            result.get("status"),
        )

        if result.get("status") in {
            "answered",
            "insufficient_evidence",
        }:
            return _response(200, result)

        return _response(500, {
            "status": "error",
            "message": (
                "No fue posible completar la consulta. "
                "Intenta nuevamente más tarde."
            ),
        })

    except Exception:
        request_id = getattr(context, "aws_request_id", "local-test")

        logger.exception(
            "Error interno al procesar consulta. request_id=%s",
            request_id,
        )

        return _response(500, {
            "status": "error",
            "message": "Error interno al procesar la consulta.",
        })
