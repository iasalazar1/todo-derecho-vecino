import unittest
from unittest.mock import patch

import retriever


class TestRetrieveHybrid(unittest.TestCase):

    # Datos de prueba definidos localmente (sin setUp)
    def get_fake_semantic_results(self):
        return [
            {
                "documento": "Ley de Establecimientos Mercantiles para la Ciudad de México",
                "articulo": "10",
                "cita_legal": "Ley de Establecimientos Mercantiles, Art. 10",
                "distancia_coseno": 0.421,
                "segmento": 0,
                "pendiente_revision": False,
                "fragmento": "Texto normativo sobre obligaciones de titulares.",
            },
            {
                "documento": "Programa Parcial de Desarrollo Urbano Hipódromo",
                "articulo": "4.4.2",
                "cita_legal": "PPCU Hipódromo, 4.4.2",
                "distancia_coseno": 0.512,
                "segmento": 1,
                "pendiente_revision": True,
                "fragmento": "Disposiciones de zonificación para la zona.",
            },
        ]

    def get_fake_structured_row(self):
        return {
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

    # 1. Recuperación semántica sin parámetros estructurados
    @patch("retriever.retrieve")
    def test_sin_parametros_estructurados_solo_ejecuta_semantica(self, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr

        res = retriever.retrieve_hybrid("¿Qué uso de suelo aplica?")

        mock_retrieve.assert_called_once()
        self.assertEqual(len(res), 2)
        self.assertTrue(all(item["tipo_evidencia"] == "semantic_chunk" for item in res))
        self.assertEqual(res[0]["articulo"], "10")

    # 2. Recuperación semántica más estructurada con parámetros válidos
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_parametros_validos_ejecuta_ambas_rutas(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr
        mock_land_use.return_value = [self.get_fake_structured_row()]

        res = retriever.retrieve_hybrid(
            question="¿Es permitida la vivienda?",
            activity="Vivienda",
            zonification="H",
        )

        mock_retrieve.assert_called_once()
        mock_land_use.assert_called_once()
        self.assertEqual(len(res), 3)
        # La primera debe ser la evidencia estructurada
        self.assertEqual(res[0]["tipo_evidencia"], "structured_row")
        self.assertEqual(res[0]["actividad_id"], "actividad_001")
        self.assertEqual(res[0]["estado_original"], "permitido")
        # Las siguientes deben ser las semánticas
        self.assertEqual(res[1]["tipo_evidencia"], "semantic_chunk")
        self.assertEqual(res[2]["tipo_evidencia"], "semantic_chunk")

    # 3. Actividad ausente
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_actividad_ausente_solo_semantica(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr

        res = retriever.retrieve_hybrid(
            question="¿Qué dice la norma?",
            activity=None,
            zonification="H",
        )

        mock_retrieve.assert_called_once()
        mock_land_use.assert_not_called()
        self.assertEqual(len(res), 2)
        self.assertTrue(all(item["tipo_evidencia"] == "semantic_chunk" for item in res))

    # 4. Zonificación ausente
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_zonificacion_ausente_solo_semantica(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr

        res = retriever.retrieve_hybrid(
            question="¿Qué dice la norma?",
            activity="Vivienda",
            zonification=None,
        )

        mock_retrieve.assert_called_once()
        mock_land_use.assert_not_called()
        self.assertEqual(len(res), 2)
        self.assertTrue(all(item["tipo_evidencia"] == "semantic_chunk" for item in res))

    # 5. Actividad inválida (vacía, espacios o tipo erróneo)
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_actividad_invalida_solo_semantica(self, mock_land_use, mock_retrieve):
        fake_sr = [
            {"documento": "Doc", "articulo": "1", "cita_legal": "C1", "distancia_coseno": 0.5,
             "segmento": 0, "pendiente_revision": False, "fragmento": "F1"},
        ]
        mock_retrieve.return_value = fake_sr

        for act in ["", "   ", 123, [], {}]:
            res = retriever.retrieve_hybrid(
                question="¿Pregunta?",
                activity=act,
                zonification="H",
            )
            self.assertEqual(len(res), 1)
            self.assertTrue(all(item["tipo_evidencia"] == "semantic_chunk" for item in res))

        mock_land_use.assert_not_called()

    # 6. Zonificación inválida (clave inexistente, vacía o tipo erróneo)
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_zonificacion_invalida_solo_semantica(self, mock_land_use, mock_retrieve):
        fake_sr = [
            {"documento": "Doc", "articulo": "1", "cita_legal": "C1", "distancia_coseno": 0.5,
             "segmento": 0, "pendiente_revision": False, "fragmento": "F1"},
        ]
        mock_retrieve.return_value = fake_sr

        for zona in ["XYZ", "", "  ", 456, ["H"]]:
            res = retriever.retrieve_hybrid(
                question="¿Pregunta?",
                activity="Vivienda",
                zonification=zona,
            )
            self.assertEqual(len(res), 1)
            self.assertTrue(all(item["tipo_evidencia"] == "semantic_chunk" for item in res))

        mock_land_use.assert_not_called()

    # 7. Consulta estructurada sin coincidencias
    # Comportamiento actualizado (integridad jurídica): una consulta ejecutada
    # correctamente sin coincidencias ya NO se responde con evidencia semántica;
    # se lanza Table22NoRecords para evitar inferir permitir/prohibir.
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_estructurada_sin_coincidencia_no_se_responde_con_semantica(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr
        mock_land_use.return_value = []

        with self.assertRaises(retriever.Table22NoRecords) as ctx:
            retriever.retrieve_hybrid(
                question="¿Es permitida la actividad?",
                activity="ActividadInexistente",
                zonification="H",
            )

        mock_land_use.assert_called_once()
        self.assertIn("permitida ni prohibida", str(ctx.exception))

    # 9. Preservación de estados originales, needs_review y procedencia
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_preservacion_estados_needs_review_y_procedencia(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        rows = [
            {
                "actividad_id": "actividad_003",
                "actividad": "Agencias funerarias",
                "categoria": "Servicios",
                "subcategoria": "Servicios Básicos",
                "zonificacion": "H",
                "estado_original": "por validar",
                "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                "fuente_paginas": [80],
                "pendiente_revision": True,
            }
        ]
        mock_land_use.return_value = rows

        res = retriever.retrieve_hybrid(
            question="¿Agencias funerarias en H?",
            activity="Agencias funerarias",
            zonification="H",
        )

        struct = res[0]
        self.assertEqual(struct["tipo_evidencia"], "structured_row")
        self.assertEqual(struct["estado_original"], "por validar")
        self.assertTrue(struct["pendiente_revision"])
        self.assertEqual(struct["fuente_archivo"], "PPCU_Hipodromo-80-81.pdf")
        self.assertEqual(struct["fuente_paginas"], [80])
        self.assertEqual(struct["documento_id"], "ppdu_hipodromo")
        self.assertEqual(struct["tabla_id"], "tabla_22")

    # 10. Fusión y eliminación de duplicados
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_deduplicacion_en_fusion(self, mock_land_use, mock_retrieve):
        # Resultados semánticos con un duplicado
        sem_duplicado = list(self.get_fake_semantic_results()) + [dict(self.get_fake_semantic_results()[0])]
        mock_retrieve.return_value = sem_duplicado

        # Resultados estructurados con un duplicado
        struct_duplicado = [dict(self.get_fake_structured_row()), dict(self.get_fake_structured_row())]
        mock_land_use.return_value = struct_duplicado

        res = retriever.retrieve_hybrid(
            question="¿Vivienda en H?",
            activity="Vivienda",
            zonification="H",
        )

        # Debe haber exactamente 1 fila estructurada y 2 chunks semánticos (sin duplicados)
        self.assertEqual(len(res), 3)
        struct_items = [item for item in res if item["tipo_evidencia"] == "structured_row"]
        sem_items = [item for item in res if item["tipo_evidencia"] == "semantic_chunk"]
        self.assertEqual(len(struct_items), 1)
        self.assertEqual(len(sem_items), 2)

    # 11. Orden determinista
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_orden_determinista_structured_primero_por_actividad_id(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr
        # Varias filas estructuradas en desorden
        rows = [
            {"actividad_id": "actividad_020", "zonificacion": "H", "actividad": "B", "estado_original": "prohibido"},
            {"actividad_id": "actividad_005", "zonificacion": "H", "actividad": "A", "estado_original": "permitido"},
        ]
        mock_land_use.return_value = rows

        res = retriever.retrieve_hybrid(
            question="Consulta",
            activity="Giro",
            zonification="H",
        )

        # Las estructuradas van primero, ordenadas por actividad_id ascendente
        self.assertEqual(res[0]["actividad_id"], "actividad_005")
        self.assertEqual(res[1]["actividad_id"], "actividad_020")
        # Luego las semánticas en el orden devuelto por retrieve()
        self.assertEqual(res[2]["articulo"], "10")
        self.assertEqual(res[3]["articulo"], "4.4.2")

    # 12. Errores técnicos de recuperación estructurada: fallo tipado.
    # Comportamiento actualizado (integridad jurídica): un fallo técnico en la
    # ruta estructurada ya NO se degrada a resultados semánticos; se lanza
    # StructuredRetrievalError para que el llamador responda de forma controlada.
    @patch("retriever.retrieve")
    @patch("retriever.retrieve_land_use")
    def test_error_tecnico_en_estructurada_lanza_fallo_tipado(self, mock_land_use, mock_retrieve):
        fake_sr = self.get_fake_semantic_results()
        mock_retrieve.return_value = fake_sr
        mock_land_use.side_effect = RuntimeError("Falló conexión psql temporalmente")

        with self.assertRaises(retriever.StructuredRetrievalError):
            retriever.retrieve_hybrid(
                question="Consulta",
                activity="Vivienda",
                zonification="H",
            )

        mock_land_use.assert_called_once()


if __name__ == "__main__":
    unittest.main()
