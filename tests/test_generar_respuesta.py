import unittest
from unittest.mock import Mock

from generar_respuesta import answer_question


class TestGenerarRespuesta(unittest.TestCase):

    def setUp(self):
        self.resultados = [
            {
                "documento": "Documento legal simulado",
                "articulo": "Artículo de prueba",
                "cita_legal": "Cita de prueba",
                "segmento": 0,
                "pendiente_revision": False,
                "fragmento": (
                    "Fragmento normativo simulado para probar las citas."
                ),
            }
        ]

        self.cliente = Mock()
        self.cliente.converse.return_value = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                "La evidencia simulada respalda esta "
                                "explicación [F1]."
                            )
                        }
                    ]
                }
            }
        }

    def test_cita_valida(self):
        resultado = answer_question(
            "¿Qué establece la norma?",
            model_id="modelo-de-prueba",
            retriever_fn=lambda pregunta, top_k: self.resultados,
            bedrock_client=self.cliente,
        )

        self.assertEqual(resultado["status"], "answered")
        self.assertEqual(
            [cita["id"] for cita in resultado["citations"]],
            ["F1"],
        )
        self.cliente.converse.assert_called_once()

    def test_rechaza_cita_inexistente(self):
        self.cliente.converse.return_value = {
            "output": {
                "message": {
                    "content": [{"text": "La norma lo establece [F9]."}]
                }
            }
        }

        resultado = answer_question(
            "¿Qué establece la norma?",
            model_id="modelo-de-prueba",
            retriever_fn=lambda pregunta, top_k: self.resultados,
            bedrock_client=self.cliente,
        )

        self.assertEqual(resultado["status"], "error")
        self.assertIn(
            "identificadores no proporcionados",
            resultado["limitations"][0],
        )

    def test_sin_evidencia_no_invoca_modelo(self):
        resultado = answer_question(
            "¿Qué establece la norma?",
            model_id="modelo-de-prueba",
            retriever_fn=lambda pregunta, top_k: [],
            bedrock_client=self.cliente,
        )

        self.assertEqual(resultado["status"], "insufficient_evidence")
        self.cliente.converse.assert_not_called()

    def test_sin_modelo_configurado(self):
        resultado = answer_question(
            "¿Qué establece la norma?",
            model_id="",
            retriever_fn=lambda pregunta, top_k: self.resultados,
            bedrock_client=self.cliente,
        )

        self.assertEqual(resultado["status"], "error")
        self.assertIsNone(resultado["model_id"])
        self.cliente.converse.assert_not_called()

    def test_rechaza_pregunta_vacia(self):
        with self.assertRaises(ValueError):
            answer_question("", model_id="modelo-de-prueba")

    def test_rechaza_top_k_invalido(self):
        with self.assertRaises(ValueError):
            answer_question(
                "Pregunta válida",
                top_k=0,
                model_id="modelo-de-prueba",
            )


if __name__ == "__main__":
    unittest.main()
