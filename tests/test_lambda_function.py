import base64
import json
from types import SimpleNamespace

import pytest

import lambda_function


def api_event(payload, method="POST", base64_encoded=False):
    body = json.dumps(payload)

    if base64_encoded:
        body = base64.b64encode(body.encode("utf-8")).decode("ascii")

    return {
        "requestContext": {
            "http": {
                "method": method,
            }
        },
        "body": body,
        "isBase64Encoded": base64_encoded,
    }


def test_parse_request_valida_pregunta():
    event = api_event({"question": "¿Qué uso de suelo tiene este predio?"})

    question, top_k = lambda_function._parse_request(event)

    assert question == "¿Qué uso de suelo tiene este predio?"
    assert top_k == 5


def test_parse_request_acepta_top_k_personalizado():
    event = api_event({"question": "Consulta de prueba", "top_k": 8})

    question, top_k = lambda_function._parse_request(event)

    assert question == "Consulta de prueba"
    assert top_k == 8


def test_parse_request_acepta_body_base64():
    event = api_event(
        {"question": "Consulta codificada"},
        base64_encoded=True,
    )

    question, top_k = lambda_function._parse_request(event)

    assert question == "Consulta codificada"
    assert top_k == 5


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": 123},
        {"question": "Consulta", "top_k": True},
        {"question": "Consulta", "top_k": 0},
        {"question": "Consulta", "top_k": 11},
        {"question": "Consulta", "top_k": 2.5},
    ],
)
def test_parse_request_rechaza_datos_invalidos(payload):
    event = api_event(payload)

    with pytest.raises(ValueError):
        lambda_function._parse_request(event)


def test_parse_request_rechaza_json_invalido():
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "body": "{json incorrecto",
        "isBase64Encoded": False,
    }

    with pytest.raises(ValueError):
        lambda_function._parse_request(event)


def test_parse_request_rechaza_metodo_no_permitido():
    event = api_event(
        {"question": "Consulta"},
        method="GET",
    )

    with pytest.raises(PermissionError):
        lambda_function._parse_request(event)


def test_lambda_handler_respuesta_generada(monkeypatch):
    bedrock = object()
    monkeypatch.setattr(
        lambda_function,
        "_get_bedrock_client",
        lambda: bedrock,
    )

    def fake_answer_question(**kwargs):
        assert kwargs["question"] == "Consulta de prueba"
        assert kwargs["top_k"] == 5
        assert kwargs["bedrock_client"] is bedrock

        return {
            "status": "answered",
            "question": "Consulta de prueba",
            "answer": "Respuesta con fundamento jurídico [F1].",
            "citations": [{"id": "F1"}],
            "limitations": [],
        }

    monkeypatch.setattr(
        lambda_function,
        "answer_question",
        fake_answer_question,
    )

    response = lambda_function.lambda_handler(
        api_event({"question": "Consulta de prueba"}),
        SimpleNamespace(aws_request_id="test-123"),
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "answered"


def test_lambda_handler_insuficiencia_de_evidencia(monkeypatch):
    monkeypatch.setattr(
        lambda_function,
        "_get_bedrock_client",
        lambda: object(),
    )
    monkeypatch.setattr(
        lambda_function,
        "answer_question",
        lambda **kwargs: {
            "status": "insufficient_evidence",
            "question": "Consulta",
            "answer": "No hay evidencia suficiente.",
            "citations": [],
            "limitations": [],
        },
    )

    response = lambda_function.lambda_handler(
        api_event({"question": "Consulta"}),
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "insufficient_evidence"


def test_lambda_handler_error_de_generacion(monkeypatch):
    monkeypatch.setattr(
        lambda_function,
        "_get_bedrock_client",
        lambda: object(),
    )
    monkeypatch.setattr(
        lambda_function,
        "answer_question",
        lambda **kwargs: {"status": "error"},
    )

    response = lambda_function.lambda_handler(
        api_event({"question": "Consulta"}),
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"])["status"] == "error"


def test_lambda_handler_metodo_get_devuelve_405():
    response = lambda_function.lambda_handler(
        api_event({"question": "Consulta"}, method="GET"),
        None,
    )

    assert response["statusCode"] == 405


def test_lambda_handler_peticion_invalida_devuelve_400():
    response = lambda_function.lambda_handler(
        api_event({"question": ""}),
        None,
    )

    assert response["statusCode"] == 400


def test_lambda_handler_inyecta_retriever_aurora(monkeypatch):
    bedrock = object()
    llamadas = {}

    monkeypatch.setattr(
        lambda_function,
        "_get_bedrock_client",
        lambda: bedrock,
    )

    def fake_retrieve(**kwargs):
        llamadas.update(kwargs)
        return [{"id": "F1"}]

    monkeypatch.setattr(lambda_function, "retrieve", fake_retrieve)

    def fake_answer_question(**kwargs):
        resultados = kwargs["retriever_fn"](
            "Consulta de prueba",
            top_k=3,
        )

        assert resultados == [{"id": "F1"}]

        return {
            "status": "answered",
            "answer": "Respuesta de prueba.",
            "citations": [],
            "limitations": [],
        }

    monkeypatch.setattr(
        lambda_function,
        "answer_question",
        fake_answer_question,
    )

    response = lambda_function.lambda_handler(
        api_event({"question": "Consulta de prueba", "top_k": 3}),
        None,
    )

    assert response["statusCode"] == 200
    assert llamadas["connection_mode"] == "aurora"
    assert llamadas["client"] is bedrock
    assert llamadas["top_k"] == 3
