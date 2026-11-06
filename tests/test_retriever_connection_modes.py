
import json
import os
import unittest
from unittest.mock import MagicMock, patch

import retriever


class TestRetrieverConnectionModes(unittest.TestCase):

    def test_sql_local_usa_variables_psql(self):
        sql = retriever._build_retrieval_sql("local")

        self.assertIn(":'vector'::vector", sql)
        self.assertIn(":'question'", sql)
        self.assertIn(":candidate_k", sql)
        self.assertIn(":top_k", sql)

    def test_sql_aurora_usa_parametros_psycopg(self):
        sql = retriever._build_retrieval_sql("aurora")

        self.assertIn("%(vector)s::vector", sql)
        self.assertIn("%(question)s", sql)
        self.assertIn("%(candidate_k)s", sql)
        self.assertIn("%(top_k)s", sql)

    def test_sql_compartido_conserva_ponderacion_hibrida(self):
        local = retriever._build_retrieval_sql("local")
        aurora = retriever._build_retrieval_sql("aurora")

        self.assertIn(
            "LEAST(relevancia_textual, 1.0) * 0.08",
            local,
        )
        self.assertIn(
            "LEAST(relevancia_textual, 1.0) * 0.08",
            aurora,
        )

    def test_rechaza_modo_invalido(self):
        with self.assertRaises(ValueError):
            retriever.retrieve(
                "Pregunta de prueba",
                connection_mode="invalido",
            )

    def test_secrets_manager_recupera_credenciales(self):
        secret = {
            "host": "aurora.example.amazonaws.com",
            "port": 5432,
            "username": "tdv_admin",
            "password": "password-de-prueba",
            "dbname": "tododerechovecino",
        }

    def test_secrets_manager_usa_db_name_como_alternativa(self):
        secret = {
            "host": "aurora.example.amazonaws.com",
            "port": 5432,
            "username": "tdv_admin",
            "password": "password-de-prueba",
        }

        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }

        with patch.dict(
            os.environ,
            {"DB_NAME": "tododerechovecino"},
            clear=True,
        ):
            credentials = retriever._get_aurora_credentials(
                secret_arn="arn:aws:secretsmanager:test",
                secrets_client=secrets_client,
            )

        self.assertEqual(
            credentials["dbname"],
            "tododerechovecino",
        )

    def test_secrets_manager_prefiere_dbname_del_secreto(self):
        secret = {
            "host": "aurora.example.amazonaws.com",
            "port": 5432,
            "username": "tdv_admin",
            "password": "password-de-prueba",
            "dbname": "base_del_secreto",
        }

        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }

        with patch.dict(
            os.environ,
            {"DB_NAME": "tododerechovecino"},
            clear=True,
        ):
            credentials = retriever._get_aurora_credentials(
                secret_arn="arn:aws:secretsmanager:test",
                secrets_client=secrets_client,
            )

        self.assertEqual(
            credentials["dbname"],
            "base_del_secreto",
        )

        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }

        credentials = retriever._get_aurora_credentials(
            secret_arn="arn:aws:secretsmanager:us-east-1:123:secret:test",
            secrets_client=secrets_client,
        )

        self.assertEqual(
            credentials["host"],
            "aurora.example.amazonaws.com",
        )
        self.assertEqual(credentials["port"], 5432)
        self.assertEqual(credentials["dbname"], "base_del_secreto")
        self.assertEqual(credentials["user"], "tdv_admin")
        self.assertEqual(credentials["password"], "password-de-prueba")

    def test_secrets_manager_rechaza_secreto_incompleto(self):
        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps({
                "host": "aurora.example.amazonaws.com",
                "username": "tdv_admin",
            })
        }

        with self.assertRaises(RuntimeError):
            retriever._get_aurora_credentials(
                secret_arn="arn:aws:secretsmanager:test",
                secrets_client=secrets_client,
            )

    def test_aurora_no_requiere_pgpassfile(self):
        secret = {
            "host": "aurora.example.amazonaws.com",
            "port": 5432,
            "username": "tdv_admin",
            "password": "password-de-prueba",
            "dbname": "tododerechovecino",
        }

        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            with patch.dict(os.environ, {}, clear=True):
                result = retriever._retrieve_aurora(
                    question="Pregunta de prueba",
                    top_k=5,
                    vector_sql="[0.1,0.2]",
                    secret_arn="arn:aws:secretsmanager:test",
                    secrets_client=secrets_client,
                )

        self.assertEqual(result, [])
        fake_psycopg.connect.assert_called_once()

        connection_args = fake_psycopg.connect.call_args.kwargs
        self.assertEqual(connection_args["port"], 5432)
        self.assertEqual(connection_args["sslmode"], "require")
        self.assertEqual(connection_args["connect_timeout"], 5)

    def test_aurora_consulta_con_parametros_esperados(self):
        secret = {
            "host": "aurora.example.amazonaws.com",
            "port": 5432,
            "username": "tdv_admin",
            "password": "password-de-prueba",
            "dbname": "tododerechovecino",
        }

        secrets_client = MagicMock()
        secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }

        fake_psycopg = MagicMock()
        fake_connection = fake_psycopg.connect.return_value.__enter__.return_value
        fake_cursor = fake_connection.cursor.return_value.__enter__.return_value
        fake_cursor.fetchone.return_value = ("[]",)

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            retriever._retrieve_aurora(
                question="¿Qué establece el programa parcial?",
                top_k=5,
                vector_sql="[0.1,0.2]",
                secret_arn="arn:aws:secretsmanager:test",
                secrets_client=secrets_client,
            )

        parameters = fake_cursor.execute.call_args.args[1]

        self.assertEqual(parameters["top_k"], 5)
        self.assertEqual(parameters["candidate_k"], 20)
        self.assertEqual(
            parameters["question"],
            "¿Qué establece el programa parcial?",
        )
        self.assertEqual(parameters["vector"], "[0.1,0.2]")


if __name__ == "__main__":
    unittest.main()
