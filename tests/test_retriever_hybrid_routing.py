"""Pruebas de enrutamiento obligatorio, errores técnicos y contrato HTTP.

Casos cubiertos (por requerimiento de corrección):
1. Pregunta de compatibilidad sin actividad ni zonificación: NO entra en
   recuperación semántica; solicita los datos faltantes.
2. Consulta con actividad y zonificación usa Tabla 22 (escenario B).
3. Pregunta general sobre Tabla 22 usa el escenario C.
4. Error técnico de PostgreSQL (psycopg) o de credenciales (Secrets
   Manager) produce StructuredRetrievalError.
5. Un error técnico en B o C nunca provoca fallback semántico.
6. Consulta ejecutada sin coincidencias produce table_22_no_matches.
7. Códigos HTTP por estado (200/200/200/503).
8. Los errores técnicos no invocan Claude ni generan respuesta jurídica
   especulativa.

Todo es offline: mocks y módulo psycopg falso; no consume AWS, Bedrock
ni Aurora. No repite baterías previas.
"""

import json
import types
import unittest
from unittest.mock import MagicMock, patch

import generar_respuesta
import lambda_function
import retriever


CONSULTA_CRITICA = "¿Puedo abrir un restaurante en la colonia Hipódromo?"
CONSULTA_GENERAL_HIPODROMO = (
    "¿Qué dice la tabla de usos de suelo del Programa Parcial de "
    "Desarrollo Urbano de la colonia Hipódromo?"
)


def semantic_results():
    return [
        {
            "documento": "Ley de Establecimientos Mercantiles",
            "articulo": "10",
            "cita_legal": "LEM, Art. 10",
            "segmento": 0,
            "pendiente_revision": False,
            "fragmento": "Texto normativo.",
        }
    ]


def fake_bedrock(answer_text=None):
    """Cliente bedrock mock: falla si converse se invoca sin texto."""
    client = MagicMock()
    if answer_text is None:
        client.converse.side_effect = AssertionError(
            "No debe invocarse el modelo generativo"
        )
    else:
        client.converse.return_value = {
            "output": {
                "message": {"content": [{"text": answer_text}]},
            }
        }
    return client


class FakePsycopgError(Exception):
    """Error falso con jerarquía mínima de psycopg para pruebas."""


def fake_psycopg_module(side_effect=None):
    """Módulo psycopg falso cuyo connect lanza FakePsycopgError."""
    module = types.ModuleType("psycopg")
    module.Error = FakePsycopgError
    module.connect = MagicMock(
        side_effect=side_effect
        or FakePsycopgError("connection to server failed")
    )
    return module


def validar_secreto():
    secret = {
        "host": "aurora.example.amazonaws.com",
        "port": 5432,
        "username": "tdv_admin",
        "password": "no-debe-aparecer-en-log",
        "dbname": "tododerechovecino",
    }
    client = MagicMock()
    client.get_secret_value.return_value = {
        "SecretString": json.dumps(secret)
    }
    return client


def nombres_de_cadena(exc):
    """Nombres de tipos en la cadena de causas de una excepción."""
    nombres = []
    actual = exc
    while actual is not None:
        nombres.append(type(actual).__name__)
        actual = actual.__cause__
    return nombres


class TestEnrutamientoCompatibilidad(unittest.TestCase):
    """1. Compatibilidad sin actividad/zonificación: no va a semántica."""

    def test_compatibilidad_sin_parametros_lanza_faltantes(self):
        with patch.object(retriever, "retrieve") as mock_retrieve:
            with self.assertRaises(
                retriever.MissingStructuredParameters
            ) as ctx:
                retriever.retrieve_hybrid(CONSULTA_CRITICA)

        # La consulta NUNCA llegó a recuperación semántica.
        mock_retrieve.assert_not_called()
        self.assertEqual(
            ctx.exception.missing_fields,
            ["activity", "zonification"],
        )

    def test_compatibilidad_sin_parametros_answer_question_controlado(self):
        bedrock = fake_bedrock(None)  # fallaría si se invocara

        def retriever_fn(q, top_k=5):
            raise retriever.MissingStructuredParameters(
                "Faltan actividad y zonificación.",
                missing_fields=["activity", "zonification"],
            )

        resultado = generar_respuesta.answer_question(
            CONSULTA_CRITICA,
            model_id="modelo-fake",
            retriever_fn=retriever_fn,
            bedrock_client=bedrock,
        )

        self.assertEqual(
            resultado["status"], "missing_structured_parameters"
        )
        self.assertEqual(
            resultado["missing_fields"], ["activity", "zonification"]
        )
        self.assertEqual(resultado["citations"], [])
        self.assertEqual(resultado["answer"], "")
        # Solo solicita los datos faltantes; sin conclusión jurídica.
        self.assertIn("zonification", resultado["limitations"][1])
        bedrock.converse.assert_not_called()

    def test_compatibilidad_sin_parametros_handler_http_200(self):
        event = {"body": json.dumps({"question": CONSULTA_CRITICA})}
        bedrock = MagicMock()

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=bedrock
        ):
            response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["status"], "missing_structured_parameters")
        self.assertEqual(
            body["missing_fields"], ["activity", "zonification"]
        )
        bedrock.converse.assert_not_called()

    def test_mencion_hipodromo_sin_intencion_permite_semantica(self):
        # No toda mención de Hipódromo es una consulta de Tabla 22.
        pregunta = "¿Qué artículos contiene el PPCU Hipódromo?"
        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ) as mock_retrieve:
            res = retriever.retrieve_hybrid(pregunta)

        mock_retrieve.assert_called_once()
        self.assertTrue(
            all(
                item["tipo_evidencia"] == "semantic_chunk"
                for item in res
            )
        )

    def test_consulta_semantica_legitima_no_requiere_tabla_22(self):
        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ) as mock_retrieve:
            res = retriever.retrieve_hybrid(
                "¿Qué dice la Ley de Cultura Cívica sobre ruidos molestos?"
            )

        mock_retrieve.assert_called_once()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["tipo_evidencia"], "semantic_chunk")


class TestEnrutamientoEscenariosByC(unittest.TestCase):
    """2 y 3. Escenario B con parámetros; escenario C para generales."""

    def test_actividad_y_zonificacion_usan_tabla_22(self):
        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ) as mock_retrieve:
            with patch.object(
                retriever, "retrieve_land_use"
            ) as mock_land_use:
                mock_land_use.return_value = [
                    {
                        "actividad_id": "actividad_001",
                        "actividad": "Vivienda",
                        "categoria": "Habitación",
                        "subcategoria": "Vivienda",
                        "zonificacion": "H",
                        "estado_original": "permitido",
                        "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                        "fuente_paginas": [80],
                        "pendiente_revision": True,
                    }
                ]
                res = retriever.retrieve_hybrid(
                    "¿Es permitida la vivienda?",
                    activity="Vivienda",
                    zonification="H",
                )

        mock_retrieve.assert_called_once()
        mock_land_use.assert_called_once()
        self.assertEqual(res[0]["tipo_evidencia"], "structured_row")
        self.assertEqual(res[0]["estado_original"], "permitido")

    def test_pregunta_general_usa_escenario_c(self):
        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ):
            with patch.object(
                retriever, "retrieve_table_22_general"
            ) as mock_general:
                mock_general.return_value = [
                    {
                        "actividad_id": "actividad_001",
                        "actividad": "Vivienda",
                        "categoria": "Habitación",
                        "subcategoria": "Vivienda",
                        "estados_por_zonificacion": [],
                        "pendiente_revision": True,
                        "tipo_evidencia": "structured_table_summary",
                    }
                ]
                res = retriever.retrieve_hybrid(
                    CONSULTA_GENERAL_HIPODROMO
                )

        mock_general.assert_called_once()
        self.assertEqual(res[0]["tipo_evidencia"], "structured_table_summary")


class TestErroresTecnicosTipados(unittest.TestCase):
    """4 y 5. Errores técnicos de psycopg/Secrets Manager y sin fallback."""

    def test_error_secrets_manager_produce_fallo_tipado(self):
        secrets_client = MagicMock()
        secrets_client.get_secret_value.side_effect = Exception(
            "AccessDeniedException"
        )

        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ):
            with self.assertRaises(
                retriever.StructuredRetrievalError
            ) as ctx:
                retriever.retrieve_hybrid(
                    "¿Es permitida la vivienda?",
                    activity="Vivienda",
                    zonification="H",
                    connection_mode="aurora",
                    secret_arn="arn:aws:secretsmanager:test",
                    secrets_client=secrets_client,
                )

        # La cadena conserva el diagnóstico para los logs:
        # StructuredRetrievalError -> RuntimeError -> Exception original.
        self.assertEqual(
            nombres_de_cadena(ctx.exception),
            ["StructuredRetrievalError", "RuntimeError", "Exception"],
        )

    def test_error_psycopg_produce_fallo_tipado(self):
        fake_psycopg = fake_psycopg_module()

        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ):
            with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
                with self.assertRaises(
                    retriever.StructuredRetrievalError
                ) as ctx:
                    retriever.retrieve_hybrid(
                        "¿Es permitida la vivienda?",
                        activity="Vivienda",
                        zonification="H",
                        connection_mode="aurora",
                        secret_arn="arn:aws:secretsmanager:test",
                        secrets_client=validar_secreto(),
                    )

        # La cadena conserva el diagnóstico:
        # StructuredRetrievalError -> RuntimeError -> psycopg.Error falso.
        self.assertEqual(
            nombres_de_cadena(ctx.exception),
            ["StructuredRetrievalError", "RuntimeError", "FakePsycopgError"],
        )

    def test_error_psycopg_escenario_c_produce_fallo_tipado(self):
        fake_psycopg = fake_psycopg_module()

        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ):
            with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
                with self.assertRaises(
                    retriever.StructuredRetrievalError
                ):
                    retriever.retrieve_hybrid(
                        CONSULTA_GENERAL_HIPODROMO,
                        connection_mode="aurora",
                        secret_arn="arn:aws:secretsmanager:test",
                        secrets_client=validar_secreto(),
                    )

    def test_fallo_tecnico_no_cae_a_semantica_con_evidencia_disponible(self):
        # Hay resultados semánticos disponibles, pero el error técnico de la
        # ruta estructurada NO debe responder con ellos.
        with patch.object(
            retriever, "retrieve", return_value=semantic_results()
        ):
            with patch.object(
                retriever,
                "retrieve_land_use",
                side_effect=RuntimeError("Aurora caída"),
            ):
                with self.assertRaises(
                    retriever.StructuredRetrievalError
                ):
                    retriever.retrieve_hybrid(
                        "¿Es permitida la veterinaria?",
                        activity="Veterinaria",
                        zonification="E",
                    )


class TestSinCoincidenciasYContrato(unittest.TestCase):
    """6 y 7. table_22_no_matches y códigos HTTP por estado."""

    def test_sin_coincidencias_status_y_http(self):
        event = {
            "body": json.dumps(
                {
                    "question": "¿Es permitida la veterinaria?",
                    "activity": "Veterinaria",
                    "zonification": "E",
                }
            )
        }

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=MagicMock()
        ):
            with patch.dict(
                "os.environ", {"BEDROCK_MODEL_ID": "modelo-fake"}
            ):
                with patch.object(
                    lambda_function, "retrieve_hybrid",
                    side_effect=retriever.Table22NoRecords(
                        "sin coincidencias"
                    ),
                ):
                    response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["status"], "table_22_no_matches")
        # Sin conclusión jurídica en la respuesta técnica.
        self.assertEqual(body["citations"], [])

    def test_fallo_tecnico_http_503(self):
        event = {
            "body": json.dumps(
                {
                    "question": "¿Es permitida la veterinaria?",
                    "activity": "Veterinaria",
                    "zonification": "E",
                }
            )
        }

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=MagicMock()
        ):
            with patch.dict(
                "os.environ", {"BEDROCK_MODEL_ID": "modelo-fake"}
            ):
                with patch.object(
                    lambda_function, "retrieve_hybrid",
                    side_effect=retriever.StructuredRetrievalError("falló"),
                ):
                    response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 503)
        self.assertEqual(body["status"], "structured_retrieval_error")

    def test_status_answered_http_200(self):
        pregunta_semantica = (
            "¿Qué dice la Ley de Cultura Cívica sobre ruidos?"
        )
        event = {"body": json.dumps({"question": pregunta_semantica})}
        with patch.object(
            lambda_function, "retrieve", return_value=semantic_results()
        ):
            with patch.object(
                lambda_function, "answer_question",
                return_value={
                    "status": "answered",
                    "question": pregunta_semantica,
                    "answer": "La ley establece [F1].",
                    "citations": [{"id": "F1"}],
                    "limitations": [],
                    "model_id": "modelo-fake",
                },
            ):
                response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["status"], "answered")


class TestErroresSinClaude(unittest.TestCase):
    """8. Los errores técnicos no invocan Claude en ninguna capa."""

    def test_answer_question_error_tecnico_no_invoca_claude(self):
        bedrock = fake_bedrock(None)

        def retriever_fn(q, top_k=5):
            raise retriever.StructuredRetrievalError("falló la consulta")

        resultado = generar_respuesta.answer_question(
            "¿Vivienda en H?",
            model_id="modelo-fake",
            retriever_fn=retriever_fn,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "structured_retrieval_error")
        bedrock.converse.assert_not_called()

    def test_answer_question_sin_coincidencias_no_invoca_claude(self):
        bedrock = fake_bedrock(None)

        def retriever_fn(q, top_k=5):
            raise retriever.Table22NoRecords("sin coincidencias")

        resultado = generar_respuesta.answer_question(
            "¿Es permitida la veterinaria en E?",
            model_id="modelo-fake",
            retriever_fn=retriever_fn,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "table_22_no_matches")
        self.assertEqual(resultado["citations"], [])
        bedrock.converse.assert_not_called()

    def test_handler_503_sin_cuerpo_juridico(self):
        event = {
            "body": json.dumps({"question": CONSULTA_GENERAL_HIPODROMO})
        }
        bedrock = fake_bedrock(None)

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=bedrock
        ):
            with patch.object(
                lambda_function, "retrieve_hybrid",
                side_effect=retriever.StructuredRetrievalError("falló"),
            ):
                with patch.dict(
                    "os.environ", {"BEDROCK_MODEL_ID": "modelo-fake"}
                ):
                    response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 503)
        self.assertEqual(body["status"], "structured_retrieval_error")
        self.assertEqual(body["answer"], "")
        # Sin afirmar permitido ni prohibido.
        self.assertNotIn("permitid", body["answer"])
        self.assertNotIn("prohibid", body["answer"])
        bedrock.converse.assert_not_called()

    def test_handler_table_22_no_matches_sin_cuerpo_juridico(self):
        event = {
            "body": json.dumps({"question": CONSULTA_GENERAL_HIPODROMO})
        }
        bedrock = fake_bedrock(None)

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=bedrock
        ):
            with patch.object(
                lambda_function, "retrieve_hybrid",
                side_effect=retriever.Table22NoRecords("sin registros"),
            ):
                with patch.dict(
                    "os.environ", {"BEDROCK_MODEL_ID": "modelo-fake"}
                ):
                    response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["status"], "table_22_no_matches")
        # Sin afirmar permitido ni prohibido.
        self.assertNotIn("permitid", body["answer"])
        self.assertNotIn("prohibid", body["answer"])
        bedrock.converse.assert_not_called()

    def test_handler_missing_params_sin_conclusion(self):
        event = {"body": json.dumps({"question": CONSULTA_CRITICA})}
        bedrock = fake_bedrock(None)

        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=bedrock
        ):
            response = lambda_function.lambda_handler(event, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["status"], "missing_structured_parameters")
        # Sin afirmar permitido ni prohibido y solo pide los datos faltantes.
        self.assertNotIn("permitid", body["answer"])
        self.assertNotIn("prohibid", body["answer"])
        self.assertEqual(
            body["missing_fields"], ["activity", "zonification"]
        )
        bedrock.converse.assert_not_called()

    def test_con_evidencia_estructurada_si_se_invoca_claude(self):
        # Control negativo: cuando SÍ hay evidencia estructurada, el flujo
        # normal invoca al modelo y devuelve answered.
        bedrock = MagicMock()
        bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "Responde [F1]."}]}}
        }

        def retriever_fn(q, top_k=5):
            return [
                {
                    "actividad_id": "actividad_001",
                    "actividad": "Vivienda",
                    "categoria": "Habitación",
                    "subcategoria": "Vivienda",
                    "zonificacion": "H",
                    "estado_original": "permitido",
                    "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                    "fuente_paginas": [80],
                    "pendiente_revision": True,
                    "tipo_evidencia": "structured_row",
                }
            ]

        resultado = generar_respuesta.answer_question(
            "¿Es permitida la vivienda en H?",
            model_id="modelo-fake",
            retriever_fn=retriever_fn,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "answered")
        self.assertEqual(resultado["citations"][0]["id"], "F1")
        bedrock.converse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
