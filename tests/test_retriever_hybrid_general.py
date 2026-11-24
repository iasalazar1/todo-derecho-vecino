"""Pruebas de la modalidad C: recuperación general de Tabla 22 (PPCU Hipódromo).

Cubre:
- Detección de preguntas generales (is_general_table_22_question).
- Recuperador general (retrieve_table_22_general): SQL, modos local/aurora.
- Integración del Escenario C en retrieve_hybrid.
- Construcción de contexto con resúmenes estructurados (generar_respuesta).

Pruebas unitarias offline: no requieren Aurora, psql ni AWS.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import generar_respuesta
import retriever


CONSULTA_GENERAL_HIPODROMO = (
    "¿Qué dice la tabla de usos de suelo del Programa Parcial de "
    "Desarrollo Urbano de la colonia Hipódromo?"
)


def fake_summary_row():
    """Resumen por actividad con procedencia diferenciada por zonificación.

    Estructura nueva (jsonb_agg con procedencia por celda): cada zonificación
    conserva su propio estado literal, fuente, páginas y needs_review.
    """
    def celda(zona, estado, pagina):
        return {
            "zonificacion": zona,
            "estado_original": estado,
            "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
            "fuente_paginas": [pagina],
            "needs_review": True,
        }

    return {
        "actividad_id": "actividad_001",
        "actividad": "Vivienda",
        "categoria": "Habitación",
        "subcategoria": "Vivienda",
        "estados_por_zonificacion": [
            celda("H", "permitido", 80),
            celda("HC", "permitido", 80),
            celda("HO", "permitido", 80),
            celda("HM", "permitido", 80),
            celda("HCS", "por validar", 80),
            celda("E", "prohibido", 81),
            celda("EA", "prohibido", 81),
        ],
        "pendiente_revision": True,
        "tipo_evidencia": "structured_table_summary",
    }


class TestDeteccionPreguntaGeneral(unittest.TestCase):
    """Detección de preguntas generales sobre Tabla 22."""

    def test_consulta_objetivo_es_general(self):
        self.assertTrue(
            retriever.is_general_table_22_question(CONSULTA_GENERAL_HIPODROMO)
        )

    def test_variante_tabla_compatibilidad_es_general(self):
        self.assertTrue(
            retriever.is_general_table_22_question(
                "¿Qué dice la tabla de compatibilidad del PPCU Hipódromo?"
            )
        )

    def test_tabla_22_directa_es_general(self):
        self.assertTrue(
            retriever.is_general_table_22_question(
                "¿Qué dice la tabla 22 del programa parcial Hipódromo?"
            )
        )

    def test_sin_mencion_de_tabla_no_es_general(self):
        self.assertFalse(
            retriever.is_general_table_22_question(
                "¿Qué usos del suelo permite el programa de Hipódromo?"
            )
        )

    def test_tabla_sin_referencia_al_programa_no_es_general(self):
        self.assertFalse(
            retriever.is_general_table_22_question(
                "¿Qué dice la tabla de usos de suelo de Cuauhtémoc?"
            )
        )

    def test_pregunta_especifica_de_permiso_no_es_general(self):
        self.assertFalse(
            retriever.is_general_table_22_question(
                "¿Es permitido un restaurante según la tabla de usos de "
                "suelo del PPCU Hipódromo?"
            )
        )

    def test_mencion_de_zonificacion_puntual_no_es_general(self):
        self.assertFalse(
            retriever.is_general_table_22_question(
                "¿Qué dice la tabla de usos de suelo del PPCU Hipódromo "
                "para la zona H?"
            )
        )

    def test_entrada_no_texto_no_es_general(self):
        self.assertFalse(retriever.is_general_table_22_question(None))
        self.assertFalse(retriever.is_general_table_22_question(123))


class TestRetrieveTable22General(unittest.TestCase):
    """Recuperador general de Tabla 22: SQL y modos de conexión."""

    def test_sql_aurora_usa_parametros_nombrados(self):
        sql = retriever._build_table_22_general_sql("aurora")
        self.assertIn("%(documento_id)s", sql)
        self.assertIn("%(tabla_id)s", sql)

    def test_sql_aurora_no_interpola_valores(self):
        sql = retriever._build_table_22_general_sql("aurora")
        self.assertNotIn("ppdu_hipodromo", sql)
        self.assertNotIn("tabla_22", sql)

    def test_sql_no_consulta_actividad_ni_zonificacion(self):
        for mode in ("local", "aurora"):
            sql = retriever._build_table_22_general_sql(mode)
            self.assertNotIn("actividad_original = ", sql)
            self.assertNotIn("zonificacion = ", sql)
            self.assertNotIn(":'activity'", sql)
            self.assertNotIn(":'zonification'", sql)
            self.assertIn("GROUP BY actividad_id", sql)
            # La agregación por celda conserva la procedencia de cada estado.
            self.assertIn("jsonb_agg", sql)
            self.assertIn("jsonb_build_object", sql)
            self.assertIn("BOOL_OR(needs_review)", sql)
            # La fuente/página no se comparten entre celdas con MAX()/MIN().
            self.assertNotIn("MAX(fuente_archivo)", sql)
            self.assertNotIn("MIN(fuente_paginas)", sql)
            self.assertNotIn("jsonb_object_agg", sql)

    def test_sql_aurora_preserva_campo_nota_si_existiera(self):
        # La nota no existe hoy como columna; la SQL solo agrega columnas reales.
        for mode in ("local", "aurora"):
            sql = retriever._build_table_22_general_sql(mode)
            self.assertNotIn("'nota'", sql)

    def test_sql_aurora_agrega_estados_por_zonificacion(self):
        sql = retriever._build_table_22_general_sql("aurora")
        self.assertIn("estados_por_zonificacion", sql)

    @patch("retriever._get_aurora_credentials")
    def test_aurora_usa_parametros_documento_y_tabla(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_cursor = (
            fake_psycopg.connect.return_value.__enter__.return_value
            .cursor.return_value.__enter__.return_value
        )
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever.retrieve_table_22_general(
                connection_mode="aurora",
                secret_arn="arn:aws:secretsmanager:us-east-1:123:secret:tdv",
            )

        params = fake_cursor.execute.call_args.args[1]
        self.assertEqual(params["documento_id"], "ppdu_hipodromo")
        self.assertEqual(params["tabla_id"], "tabla_22")

        connect_kwargs = fake_psycopg.connect.call_args.kwargs
        self.assertEqual(connect_kwargs["sslmode"], "require")
        self.assertEqual(connect_kwargs["connect_timeout"], 5)
        self.assertNotIn("PGPASSFILE", os.environ)

    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {"PGPASSFILE": "/tmp/pgpass_test"}, clear=True)
    @patch.object(os.path, "isfile", return_value=True)
    def test_local_usa_psql_con_variables_documento_y_tabla(
        self, mock_isfile, mock_run
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        retriever.retrieve_table_22_general(connection_mode="local")

        command = mock_run.call_args.args[0]
        self.assertIn("psql", command)
        self.assertIn("documento_id=ppdu_hipodromo", command)
        self.assertIn("tabla_id=tabla_22", command)

    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {}, clear=True)
    def test_local_requiere_pgpassfile(self, mock_run):
        with self.assertRaises(RuntimeError) as ctx:
            retriever.retrieve_table_22_general(connection_mode="local")
        self.assertIn("PGPASSFILE", str(ctx.exception))

    def test_modo_invalido_rechazado(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_table_22_general(connection_mode="otro")

    def test_normalizacion_marca_tipo_evidencia_y_orden(self):
        raw = [
            {"actividad_id": "actividad_002", "actividad": "Hoteles"},
            {"actividad_id": "actividad_001", "actividad": "Vivienda"},
        ]
        with patch.object(
            retriever,
            "_retrieve_table_22_general_local",
            return_value=raw,
        ):
            resultado = retriever.retrieve_table_22_general(
                connection_mode="local"
            )

        self.assertEqual(
            [row["actividad_id"] for row in resultado],
            ["actividad_001", "actividad_002"],
        )
        self.assertTrue(
            all(
                row["tipo_evidencia"] == "structured_table_summary"
                for row in resultado
            )
        )
        self.assertEqual(resultado[0]["documento_id"], "ppdu_hipodromo")
        self.assertEqual(resultado[0]["tabla_id"], "tabla_22")


class TestRetrieveHybridEscenarioC(unittest.TestCase):
    """Integración del Escenario C en retrieve_hybrid."""

    def setUp(self):
        self.semantics = [
            {
                "documento": "Ley de Cultura Cívica",
                "articulo": "21",
                "cita_legal": "LCC, Art. 21",
                "segmento": 0,
                "pendiente_revision": False,
                "fragmento": "Texto de prueba.",
            }
        ]

    @patch("retriever.retrieve")
    @patch("retriever.retrieve_table_22_general")
    def test_pregunta_general_recupera_resumen_de_tabla_22(
        self, mock_general, mock_retrieve
    ):
        mock_retrieve.return_value = self.semantics
        mock_general.return_value = [fake_summary_row()]

        res = retriever.retrieve_hybrid(CONSULTA_GENERAL_HIPODROMO)

        mock_general.assert_called_once()
        # La fila estructurada va primero, la semántica después.
        self.assertEqual(res[0]["tipo_evidencia"], "structured_table_summary")
        self.assertEqual(res[0]["actividad_id"], "actividad_001")
        self.assertEqual(res[0]["documento_id"], "ppdu_hipodromo")
        self.assertEqual(res[0]["tabla_id"], "tabla_22")
        self.assertEqual(res[1]["tipo_evidencia"], "semantic_chunk")

        # Los estados se conservan literalmente, con procedencia por celda.
        estados = res[0]["estados_por_zonificacion"]
        por_zona = {celda["zonificacion"]: celda for celda in estados}
        self.assertEqual(por_zona["H"]["estado_original"], "permitido")
        self.assertEqual(por_zona["E"]["estado_original"], "prohibido")
        self.assertEqual(por_zona["HCS"]["estado_original"], "por validar")
        # Procedencia propia por zonificación
        self.assertEqual(
            por_zona["H"]["fuente_archivo"], "PPCU_Hipodromo-80-81.pdf"
        )
        self.assertEqual(por_zona["E"]["fuente_paginas"], [81])
        self.assertTrue(por_zona["H"]["needs_review"])
        self.assertTrue(res[0]["pendiente_revision"])

    @patch("retriever.retrieve")
    @patch("retriever.retrieve_table_22_general")
    def test_error_tecnico_en_ruta_general_no_degrada_a_semantica(
        self, mock_general, mock_retrieve
    ):
        # Comportamiento actualizado (integridad jurídica): un fallo técnico en
        # la ruta general lanza StructuredRetrievalError; la evidencia
        # semántica no se entrega como sustituto.
        mock_retrieve.return_value = self.semantics
        mock_general.side_effect = RuntimeError("Falló conexión")

        with self.assertRaises(retriever.StructuredRetrievalError):
            retriever.retrieve_hybrid(CONSULTA_GENERAL_HIPODROMO)

        mock_general.assert_called_once()

    @patch("retriever.retrieve")
    @patch("retriever.retrieve_table_22_general")
    def test_tabla_22_sin_registros_no_se_responde_con_semantica(
        self, mock_general, mock_retrieve
    ):
        # Comportamiento actualizado (integridad jurídica): una consulta
        # correcta sin registros lanza Table22NoRecords y no permite una
        # conclusión de compatibilidad vía evidencia semántica.
        mock_retrieve.return_value = self.semantics
        mock_general.return_value = []

        with self.assertRaises(retriever.Table22NoRecords):
            retriever.retrieve_hybrid(CONSULTA_GENERAL_HIPODROMO)

    @patch("retriever.retrieve")
    @patch("retriever.retrieve_table_22_general")
    def test_escenario_b_tiene_prioridad_y_no_llama_ruta_general(
        self, mock_general, mock_retrieve
    ):
        mock_retrieve.return_value = self.semantics

        with patch("retriever.retrieve_land_use") as mock_land_use:
            mock_land_use.return_value = [
                {
                    "actividad_id": "actividad_001",
                    "actividad": "Vivienda",
                    "zonificacion": "H",
                    "estado_original": "permitido",
                    "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
                    "fuente_paginas": [80],
                    "pendiente_revision": True,
                }
            ]
            res = retriever.retrieve_hybrid(
                question=CONSULTA_GENERAL_HIPODROMO,
                activity="Vivienda",
                zonification="H",
            )

        mock_land_use.assert_called_once()
        mock_general.assert_not_called()
        self.assertEqual(res[0]["tipo_evidencia"], "structured_row")

    @patch("retriever.retrieve")
    @patch("retriever.retrieve_table_22_general")
    def test_pregunta_semantica_comun_no_activa_ruta_general(
        self, mock_general, mock_retrieve
    ):
        mock_retrieve.return_value = self.semantics

        res = retriever.retrieve_hybrid(
            "¿Qué obligaciones tiene un establecimiento mercantil con vecinos?"
        )

        mock_general.assert_not_called()
        self.assertTrue(
            all(item["tipo_evidencia"] == "semantic_chunk" for item in res)
        )


class TestContextoResumenTabla22(unittest.TestCase):
    """Construcción de contexto para evidencia estructurada general."""

    def test_resumen_genera_identificadores_y_estados_literales(self):
        context, sources = generar_respuesta._build_context(
            [fake_summary_row()]
        )

        self.assertEqual(len(sources), 1)
        source = sources[0]
        self.assertEqual(source["id"], "F1")
        self.assertTrue("[F1]" in context)

        fragmento = source["fragmento"]
        # Estados literales, sin convertir celdas ausentes ni reinterpretar.
        self.assertIn("Estado", fragmento)
        self.assertIn("permitido", fragmento)
        self.assertIn("prohibido", fragmento)
        self.assertIn("por validar", fragmento)
        self.assertIn("Habitación", fragmento)
        self.assertIn("Vivienda", fragmento)
        self.assertIn("PPCU_Hipodromo-80-81.pdf", fragmento)
        self.assertIn("80", fragmento)

    def test_resumen_preserva_pendiente_revision(self):
        _, sources = generar_respuesta._build_context([fake_summary_row()])
        self.assertTrue(sources[0]["pendiente_revision"])
        self.assertIn("Pendiente de revisión: sí", _context_for(fake_summary_row()))

    def test_resumen_sin_nota_no_incluye_nota(self):
        row = fake_summary_row()  # sin clave "nota"
        _, sources = generar_respuesta._build_context([row])
        self.assertNotIn("Nota", sources[0]["fragmento"])
        self.assertNotIn("nota", sources[0])

    def test_resumen_con_nota_relacionada_la_incluye(self):
        row = fake_summary_row()
        row["nota"] = "Los estados corresponden a la Tabla 22 del PPCU."
        _, sources = generar_respuesta._build_context([row])
        self.assertIn("Nota", sources[0]["fragmento"])
        self.assertEqual(sources[0]["nota"], row["nota"])

    def test_valores_nota_vacios_se_descartan(self):
        row = fake_summary_row()
        row["nota"] = "   "
        _, sources = generar_respuesta._build_context([row])
        self.assertNotIn("nota", sources[0])

    def test_documentos_normativos_y_metadatos_estructurados(self):
        row = fake_summary_row()
        row["documento"] = "Programa Parcial de Desarrollo Urbano Hipódromo"
        row["documento_id"] = "ppdu_hipodromo"
        row["tabla_id"] = "tabla_22"
        _, sources = generar_respuesta._build_context([row])
        source = sources[0]
        self.assertEqual(
            source["documento"],
            "Programa Parcial de Desarrollo Urbano Hipódromo",
        )
        self.assertEqual(source["documento_id"], "ppdu_hipodromo")
        self.assertEqual(source["tabla_id"], "tabla_22")
        # En el formato con procedencia por zonificación, fuente y páginas ya
        # no viven a nivel de fuente resumida sino dentro de cada celda.
        self.assertNotIn("fuente_archivo", source)
        celdas = source["estados_por_zonificacion"]
        self.assertEqual(
            celdas[0]["fuente_archivo"], "PPCU_Hipodromo-80-81.pdf"
        )
        self.assertEqual(celdas[0]["fuente_paginas"], [80])

    def test_fila_puntual_mantiene_documento_y_agrega_fuente(self):
        row = {
            "tipo_evidencia": "structured_row",
            "actividad_id": "actividad_001",
            "actividad": "Vivienda",
            "categoria": "Habitación",
            "subcategoria": "Vivienda",
            "zonificacion": "H",
            "estado_original": "permitido",
            "fuente_archivo": "PPCU_Hipodromo-80-81.pdf",
            "fuente_paginas": [80],
            "pendiente_revision": True,
            "documento": "Programa Parcial de Desarrollo Urbano Hipódromo",
        }
        _, sources = generar_respuesta._build_context([row])
        source = sources[0]
        # El documento normativo no se pierde por el archivo fuente.
        self.assertEqual(
            source["documento"],
            "Programa Parcial de Desarrollo Urbano Hipódromo",
        )
        self.assertEqual(
            source["fuente_archivo"], "PPCU_Hipodromo-80-81.pdf"
        )
        self.assertEqual(source["articulo"], "Tabla 22")
        self.assertEqual(source["estado_original"], "permitido")


def _context_for(item):
    context, _ = generar_respuesta._build_context([item])
    return context


if __name__ == "__main__":
    unittest.main()
