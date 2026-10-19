from pathlib import Path
import sys
import subprocess

import boto3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generar_embeddings import generate_embedding, DIMENSIONS

PREGUNTA = (
    "En la colonia Hipódromo, alcaldía Cuauhtémoc, "
    "¿qué disposiciones regulan la operación de un bar respecto "
    "al uso de suelo y la compatibilidad del giro con la zonificación, "
    "los horarios de funcionamiento, las emisiones de ruido "
    "y las molestias a los vecinos?"
)

DOCUMENTOS = [
    "Programa Parcial de Desarrollo Urbano Hipódromo",
    "Ley de Establecimientos Mercantiles para la Ciudad de México",
]


def main():
    cliente = boto3.client("bedrock-runtime", region_name="us-east-1")
    vector = generate_embedding(cliente, PREGUNTA)
    assert len(vector) == DIMENSIONS == 1024

    vector_sql = "[" + ",".join(str(float(x)) for x in vector) + "]"

    sql = """
    SELECT
        d.name AS documento,
        c.article AS articulo,
        c.legal_citation AS cita_legal,
        ROUND((e.embedding <=> :'vector'::vector)::numeric, 6)
            AS distancia_coseno,
        e.segment_index AS segmento,
        e.needs_review AS pendiente_revision,
        LEFT(e.segment_text, 900) AS fragmento
    FROM legal_embeddings e
    JOIN legal_documents d ON d.id = e.document_id
    JOIN legal_chunks c
      ON c.id = e.legal_chunk_id
     AND c.document_id = e.document_id
    WHERE d.name = :'documento'
    ORDER BY e.embedding <=> :'vector'::vector
    LIMIT 5;
    """

    for documento in DOCUMENTOS:
        print(f"\n{'=' * 90}\nDOCUMENTO: {documento}\n{'=' * 90}")

        entrada_psql = (
            f"\\set vector '{vector_sql}'\n"
            f"\\set documento '{documento.replace(chr(39), chr(39) * 2)}'\n"
            + sql
        )

        comando = [
            "psql", "-X", "-w",
            "-h", "127.0.0.1",
            "-p", "15432",
            "-U", "tdv_admin",
            "-d", "tododerechovecino",
            "-v", "ON_ERROR_STOP=1",
        ]

        resultado = subprocess.run(
            comando,
            input=entrada_psql,
            text=True,
        )

        if resultado.returncode != 0:
            raise SystemExit(
                f"Falló la búsqueda para {documento}; "
                f"código: {resultado.returncode}"
            )


if __name__ == "__main__":
    main()
