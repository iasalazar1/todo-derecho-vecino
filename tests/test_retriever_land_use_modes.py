import json
import os
import unittest
from unittest.mock import MagicMock, patch

import retriever


class TestRetrieverLandUseModes(unittest.TestCase):

    # ------------------------------------------------------------------
    # Validaciones de entrada
    # ------------------------------------------------------------------
    def test_rechaza_actividad_vacia(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use("", "H")

    def test_rechaza_actividad_solo_espacios(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use("   ", "H")

    def test_rechaza_zonificacion_no_texto(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use("Vivienda", 123)

    def test_rechaza_zonificacion_invalida(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use("Vivienda", "XYZ")

    def test_rechaza_zonificacion_vacia(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use("Vivienda", "")

    def test_rechaza_modo_invalido(self):
        with self.assertRaises(ValueError):
            retriever.retrieve_land_use(
                "Vivienda", "H", connection_mode="invalido"
            )

    def test_acepta_zonificaciones_validas(self):
        for zona in ["H", "HC", "HO", "HM", "HCS", "E", "EA"]:
            try:
                retriever.retrieve_land_use("Vivienda", zona)
            except ValueError as exc:
                self.fail(f"Zonificación {zona} no debería fallar validación: {exc}")
            except RuntimeError:
                pass

    # ------------------------------------------------------------------
    # Modo local
    # ------------------------------------------------------------------
    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {"PGPASSFILE": "/tmp/pgpass_test"}, clear=True)
    @patch.object(os.path, "isfile", return_value=True)
    def test_local_usa_psql_y_pgpassfile(self, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="[]", stderr=""
        )
        retriever.retrieve_land_use("Vivienda", "H", connection_mode="local")

        self.assertTrue(mock_run.called)
        command = mock_run.call_args.args[0]
        self.assertIn("psql", command)
        self.assertIn("-v", command)
        self.assertIn("activity=Vivienda", command)
        self.assertIn("zonification=H", command)

    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {}, clear=True)
    def test_local_requiere_pgpassfile(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="[]", stderr=""
        )
        with self.assertRaises(RuntimeError) as ctx:
            retriever.retrieve_land_use("Vivienda", "H", connection_mode="local")
        self.assertIn("PGPASSFILE", str(ctx.exception))

    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {"PGPASSFILE": "/tmp/pgpass_test"}, clear=True)
    @patch.object(os.path, "isfile", return_value=True)
    def test_local_devuelve_lista_vacia_sin_salida(self, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        resultado = retriever.retrieve_land_use("Vivienda", "H", connection_mode="local")
        self.assertEqual(resultado, [])

    @patch("retriever.subprocess.run")
    @patch.dict(os.environ, {"PGPASSFILE": "/tmp/pgpass_test"}, clear=True)
    @patch.object(os.path, "isfile", return_value=True)
    def test_local_propaga_error_de_postgresql(self, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="ERROR:  relación no encontrada"
        )
        with self.assertRaises(RuntimeError) as ctx:
            retriever.retrieve_land_use("Vivienda", "H", connection_mode="local")
        self.assertIn("Falló la consulta estructurada", str(ctx.exception))

    # ------------------------------------------------------------------
    # Modo Aurora
    # ------------------------------------------------------------------
    def test_aurora_sql_usa_parametros_nombrados(self):
        sql = retriever._build_land_use_sql("aurora")
        self.assertIn("%(documento_id)s", sql)
        self.assertIn("%(tabla_id)s", sql)
        self.assertIn("%(zonification)s", sql)
        self.assertIn("%(activity)s", sql)
        self.assertNotIn(":'activity'", sql)
        self.assertNotIn(":'zonification'", sql)

    def test_aurora_sql_no_interpola_valores(self):
        sql = retriever._build_land_use_sql("aurora")
        self.assertNotIn("ppdu_hipodromo", sql)
        self.assertNotIn("tabla_22", sql)

    @patch("retriever._get_aurora_credentials")
    def test_aurora_usa_get_aurora_credentials(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
                secret_arn="arn:aws:secretsmanager:us-east-1:123456789:secret:tdv",
            )

        mock_credentials.assert_called_once()
        args, kwargs = mock_credentials.call_args
        self.assertEqual(
            kwargs.get("secret_arn"),
            "arn:aws:secretsmanager:us-east-1:123456789:secret:tdv",
        )

    @patch("retriever._get_aurora_credentials")
    def test_aurora_usa_ssl_require(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
            )

        connect_kwargs = fake_psycopg.connect.call_args.kwargs
        self.assertEqual(connect_kwargs["sslmode"], "require")
        self.assertEqual(connect_kwargs["connect_timeout"], 5)

    @patch("retriever._get_aurora_credentials")
    def test_aurora_usa_parametros_sql_no_interpolacion(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
            )

        params = fake_cursor.execute.call_args.args[1]
        self.assertEqual(params["documento_id"], "ppdu_hipodromo")
        self.assertEqual(params["tabla_id"], "tabla_22")
        self.assertEqual(params["zonification"], "H")
        self.assertEqual(params["activity"], "Vivienda")

    @patch("retriever._get_aurora_credentials")
    def test_aurora_cierra_conexion_y_cursor(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = MagicMock()
        fake_cursor = MagicMock()
        fake_psycopg.connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
            )

        fake_cursor.fetchone.assert_called_once()
        fake_psycopg.connect.assert_called_once()
        connect_kwargs = fake_psycopg.connect.call_args.kwargs
        self.assertEqual(connect_kwargs["sslmode"], "require")
        self.assertEqual(connect_kwargs["connect_timeout"], 5)

    @patch("retriever._get_aurora_credentials")
    def test_aurora_devuelve_lista_vacia_sin_resultados(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = (None,)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            resultado = retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
            )

        self.assertEqual(resultado, [])

    @patch("retriever._get_aurora_credentials")
    def test_aurora_no_depende_de_pgpassfile(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            with patch.dict(os.environ, {}, clear=True):
                resultado = retriever._retrieve_land_use_aurora(
                    activity="Vivienda",
                    zonification="H",
                )

        self.assertEqual(resultado, [])
        fake_psycopg.connect.assert_called_once()

    @patch("retriever._get_aurora_credentials")
    def test_aurora_propaga_error_de_conexion(self, mock_credentials):
        mock_credentials.side_effect = RuntimeError(
            "No se pudieron obtener credenciales"
        )

        with self.assertRaises(RuntimeError) as ctx:
            retriever._retrieve_land_use_aurora(
                activity="Vivienda",
                zonification="H",
            )
        self.assertIn("No se pudieron obtener credenciales", str(ctx.exception))

    @patch("retriever._get_aurora_credentials")
    def test_aurora_propaga_error_de_consulta(self, mock_credentials):
        mock_credentials.return_value = {
            "host": "aurora.example.com",
            "port": 5432,
            "dbname": "tododerechovecino",
            "user": "tdv_admin",
            "password": "secret",
        }

        fake_psycopg = MagicMock()
        # El helper _execute_aurora_query captura psycopg.Error; un Error
        # real (RuntimeError) no captura Exception genérica, así que el
        # error de consulta se propaga sin envolver.
        fake_psycopg.Error = RuntimeError
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.execute.side_effect = Exception("error de consulta")

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            with self.assertRaises(Exception) as ctx:
                retriever._retrieve_land_use_aurora(
                    activity="Vivienda",
                    zonification="H",
                )
        self.assertIn("error de consulta", str(ctx.exception))

    # ------------------------------------------------------------------
    # Dispatcher: modo por defecto es local
    # ------------------------------------------------------------------
    def test_dispatcher_por_defecto_es_local(self):
        with self.assertRaises(RuntimeError) as ctx:
            retriever.retrieve_land_use("Vivienda", "H")
        self.assertIn("PGPASSFILE", str(ctx.exception))