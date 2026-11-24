"""Pruebas de integridad jurídica del recuperador híbrido A/B/C.

Casos cubiertos (por requerimiento de corrección):
1. Fallo técnico de recuperación estructurada en escenario B.
2. Fallo técnico de recuperación estructurada en escenario C.
3. Resultado estructurado vacío (B y C): sin conclusiones de compatibilidad.
4. Procedencia diferenciada por zonificación (fuente/página propias por celda).
5. Estado con asterisco y nota recuperada.
6. Estado con asterisco y nota no recuperable (advertencia explícita).

Todo es offline: mocks y datos locales; no consume AWS, Bedrock ni Aurora.
No repite la batería completa previa.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import generar_respuesta
import lambda_function
import retriever


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


def row_con_procedencia_diferenciada():
    """Vivienda con fuente/página distintas por zonificación."""
    return {
        "actividad_id": "actividad_001",
        "actividad": "Vivienda",
        "categoria": "Habitación",
        "subcategoria": "Vivienda",
        "estados_por_zonificacion": [
            {
                "zonificacion": "H",
                "estado_original": "permitido",
                "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                "fuente_paginas": [80],
                "needs_review": True,
            },
            {
                "zonificacion": "E",
                "estado_original": "prohibido",
                "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                "fuente_paginas": [81],
                "needs_review": True,
            },
        ],
        "pendiente_revision": True,
        "tipo_evidencia": "structured_table_summary",
    }


def row_con_asterisco_y_nota():
    return {
        "actividad_id": "actividad_029",
        "actividad": "Alojamiento y desayuno (B&B)",
        "categoria": "Habitación",
        "subcategoria": "Alojamiento",
        "estados_por_zonificacion": [
            {
                "zonificacion": "H",
                "estado_original": "permitido (**)",
                "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                "fuente_paginas": [81],
                "needs_review": True,
                "nota": "Solo en predios señalados en el plano.",
            },
        ],
        "pendiente_revision": True,
        "tipo_evidencia": "structured_table_summary",
    }


def row_con_asterisco_sin_nota():
    row = row_con_asterisco_y_nota()
    row["estados_por_zonificacion"][0].pop("nota")
    return row


def fake_bedrock(answer_text):
    """Cliente bedrock mock con estructura Converse; falla si se invoca a menos que text."""
    client = MagicMock()
    if answer_text is None:
        client.converse.side_effect = AssertionError(
            "No debe invocarse el modelo generativo"
        )
    else:
        client.converse.return_value = {
            "output": {
                "message": {
                    "content": [{"text": answer_text}],
                }
            }
        }
    return client


class TestEscenarioBFalloTecnico(unittest.TestCase):
    """1. Fallo técnico en recuperación estructurada puntual."""

    def test_fallo_tecnico_lanza_fallo_tipado(self):
        with patch.object(retriever, "retrieve", return_value=semantic_results()):
            with patch.object(
                retriever, "retrieve_land_use",
                side_effect=RuntimeError("psql no disponible"),
            ):
                with self.assertRaises(retriever.StructuredRetrievalError):
                    retriever.retrieve_hybrid(
                        "¿Actividad?", activity="Vivienda", zonification="H"
                    )

    def test_answer_question_responde_controlado_sin_llamar_a_claude(self):
        bedrock = fake_bedrock(None)  # fallaría si se invocara
        def retriever_roto(q, top_k=5):
            raise retriever.StructuredRetrievalError(
                "No fue posible consultar la evidencia estructurada"
            )
        resultado = generar_respuesta.answer_question(
            "¿Vivienda en H?",
            model_id="modelo-fake",
            retriever_fn=retriever_roto,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "structured_retrieval_error")
        self.assertEqual(resultado["citations"], [])
        self.assertIn(
            "la recuperación semántica no se usó como sustituto",
            " ".join(resultado["limitations"]),
        )
        bedrock.converse.assert_not_called()

    def test_lambda_handler_reconoce_el_fallo(self):
        event = {
            "body": json.dumps(
                {
                    "question": "¿Vivienda en H?",
                    "activity": "Vivienda",
                    "zonification": "H",
                }
            )
        }
        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=MagicMock()
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
        # Contrato HTTP: structured_retrieval_error ahora es 503.
        self.assertEqual(response["statusCode"], 503)
        self.assertEqual(body["status"], "structured_retrieval_error")
        self.assertEqual(body["citations"], [])

    def test_lambda_handler_reconoce_el_fallo_escenario_c(self):
        event = {"body": json.dumps({"question": CONSULTA_GENERAL_HIPODROMO})}
        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=MagicMock()
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


class TestEscenarioCFalloTecnico(unittest.TestCase):
    """2. Fallo técnico en recuperación general de Tabla 22."""

    def test_fallo_tecnico_lanza_fallo_tipado(self):
        with patch.object(retriever, "retrieve", return_value=semantic_results()):
            with patch.object(
                retriever, "retrieve_table_22_general",
                side_effect=RuntimeError("Aurora inaccesible"),
            ):
                with self.assertRaises(retriever.StructuredRetrievalError):
                    retriever.retrieve_hybrid(CONSULTA_GENERAL_HIPODROMO)

    def test_answer_question_responde_controlado_sin_llamar_a_claude(self):
        bedrock = fake_bedrock(None)
        def retriever_roto(q, top_k=5):
            raise retriever.StructuredRetrievalError(
                "No fue posible consultar la evidencia estructurada"
            )
        resultado = generar_respuesta.answer_question(
            CONSULTA_GENERAL_HIPODROMO,
            model_id="modelo-fake",
            retriever_fn=retriever_roto,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "structured_retrieval_error")
        # La pregunta general no se responde con los fragmentos semánticos.
        self.assertEqual(resultado["answer"], "")
        bedrock.converse.assert_not_called()

    def test_lambda_handler_reconoce_el_fallo(self):
        event = {"body": json.dumps({"question": CONSULTA_GENERAL_HIPODROMO})}
        with patch.object(
            lambda_function, "_get_bedrock_client", return_value=MagicMock()
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
        # Contrato HTTP: structured_retrieval_error ahora es 503.
        self.assertEqual(response["statusCode"], 503)
        self.assertEqual(body["status"], "structured_retrieval_error")


class TestResultadoEstructuradoVacio(unittest.TestCase):
    """3. Consulta correcta sin coincidencias: distinto del fallo técnico."""

    def test_escenario_b_sin_coincidencia_lanza_tipado_distinto(self):
        with patch.object(retriever, "retrieve", return_value=semantic_results()):
            with patch.object(retriever, "retrieve_land_use", return_value=[]):
                with self.assertRaises(retriever.Table22NoRecords) as ctx:
                    retriever.retrieve_hybrid(
                        "¿Actividad?", activity="ActividadInexistente",
                        zonification="H",
                    )
        self.assertIn("permitida ni prohibida", str(ctx.exception))

    def test_escenario_c_sin_registros_lanza_tipado_distinto(self):
        with patch.object(retriever, "retrieve", return_value=semantic_results()):
            with patch.object(
                retriever, "retrieve_table_22_general", return_value=[]
            ):
                with self.assertRaises(retriever.Table22NoRecords) as ctx:
                    retriever.retrieve_hybrid(CONSULTA_GENERAL_HIPODROMO)
        self.assertIn("No puede presentarse una conclusión", str(ctx.exception))

    def test_answer_question_sin_coincidencias_no_llama_a_claude(self):
        bedrock = fake_bedrock(None)
        def retriever_sin_coincidencias(q, top_k=5):
            raise retriever.Table22NoRecords(
                "La consulta estructurada se ejecutó correctamente pero no "
                "encontró coincidencias."
            )
        resultado = generar_respuesta.answer_question(
            "¿Vivienda en H?",
            model_id="modelo-fake",
            retriever_fn=retriever_sin_coincidencias,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "table_22_no_matches")
        self.assertIn(
            "no implica permiso ni prohibición",
            " ".join(resultado["limitations"]),
        )
        bedrock.converse.assert_not_called()

    def test_los_tipos_de_resultado_son_distintos_entre_si(self):
        # El caso sin coincidencias no debe confundirse con el fallo técnico.
        self.assertNotEqual(
            retriever.Table22NoRecords("sin coincidencias"),
            retriever.StructuredRetrievalError("fallo técnico"),
        )


class TestProcedenciaPorZonificacion(unittest.TestCase):
    """4. Cada estado conserva su propia fuente y página."""

    def test_fragmento_muestra_procedencia_por_celda(self):
        context, sources = generar_respuesta._build_context(
            [row_con_procedencia_diferenciada()]
        )
        fragmento = sources[0]["fragmento"]
        # H: página 80
        self.assertIn(
            "Zonificación H — Estado (literal): permitido", fragmento
        )
        self.assertIn(
            "Fuente: PPCU_Hipodromo-80-81.pdf | Páginas: 80", fragmento
        )
        # E: página 81 (fuente/página propias, no compartidas)
        self.assertIn(
            "Zonificación E — Estado (literal): prohibido", fragmento
        )
        self.assertIn(
            "Fuente: PPCU_Hipodromo-80-81.pdf | Páginas: 81", fragmento
        )
        # Marca de revisión por celda
        self.assertIn("Pendiente de revisión: sí", fragmento)
        self.assertTrue(context)  # el bloque [F1] existe

    def test_identificadores_de_cita_se_conservan(self):
        _, sources = generar_respuesta._build_context(
            [row_con_procedencia_diferenciada(), *semantic_results()]
        )
        self.assertEqual(sources[0]["id"], "F1")
        self.assertEqual(sources[1]["id"], "F2")
        # El fragmento semántico llega intacto.
        self.assertEqual(
            sources[1]["fragmento"], "Texto normativo."
        )


class TestEstadoConAsterisco(unittest.TestCase):
    """5 y 6. Estados con asterisco con y sin nota recuperable."""

    def test_nota_recuperada_se_presenta_y_no_amerita_advertencia(self):
        # 5. Relación comprobable: la nota viene en el propio registro.
        _, sources = generar_respuesta._build_context([row_con_asterisco_y_nota()])
        source = sources[0]
        fragmento = source["fragmento"]
        self.assertIn("Estado (literal): permitido (**)", fragmento)
        self.assertIn("Nota: Solo en predios señalados en el plano.", fragmento)
        self.assertNotIn("advertencia_nota_pendiente", source)
        self.assertNotIn("pendiente de interpretación", fragmento)

    def test_nota_no_recuperable_genera_advertencia_explícita(self):
        # 6. Asterisco sin nota disponible: advertencia explícita.
        _, sources = generar_respuesta._build_context([row_con_asterisco_sin_nota()])
        source = sources[0]
        fragmento = source["fragmento"]
        # El estado se preserva literalmente.
        self.assertIn("Estado (literal): permitido (**)", fragmento)
        # La advertencia llega al contexto de Claude...
        self.assertIn("pendiente de interpretación", fragmento)
        self.assertIn("No debe interpretarse como autorización incondicional",
                      fragmento)
        # ...y queda reflejada en la evidencia/cita.
        self.assertTrue(source.get("advertencia_nota_pendiente"))
        self.assertEqual(
            source.get("estados_claves_con_asterisco_sin_nota"), ["H"]
        )

    def test_advertencia_pasa_a_limitaciones_de_la_respuesta(self):
        # El caso 5 también puede probarse con mocks: bedrock mock-await...
        bedrock = fake_bedrock(
            "El estado del giro es permitido (**) [F1], con condición "
            "pendiente de interpretación."
        )
        def retriever_con_asterisco(q, top_k=5):
            return [dict(row_con_asterisco_sin_nota())]
        resultado = generar_respuesta.answer_question(
            "¿Alojamiento y desayuno (B&B) en la zona H del hipódromo?",
            model_id="modelo-fake",
            retriever_fn=retriever_con_asterisco,
            bedrock_client=bedrock,
        )
        self.assertEqual(resultado["status"], "answered")
        advertencias = [
            lim for lim in resultado["limitations"]
            if "asterisco" in lim and "no está disponible" in lim
        ]
        self.assertEqual(len(advertencias), 1)
        # La cita refleja la advertencia.
        self.assertTrue(
            resultado["citations"][0].get("advertencia_nota_pendiente")
        )

    def test_estado_asteriscado_no_se_normaliza(self):
        # El estado 'permitido (**)' nunca se reduce a 'permitido'.
        context, sources = generar_respuesta._build_context(
            [row_con_asterisco_sin_nota()]
        )
        self.assertIn("Estado (literal): permitido (**)", context)
        self.assertIn("Estado (literal): permitido (**)", sources[0]["fragmento"])
        self.assertNotIn(
            "Estado (literal): permitido |", sources[0]["fragmento"]
        )


if __name__ == "__main__":
    unittest.main()
