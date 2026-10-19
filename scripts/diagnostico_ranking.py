import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import os
import subprocess

import boto3
from generar_embeddings import generate_embedding, DIMENSIONS

QUESTION = (
    "¿Qué obligaciones tienen los establecimientos mercantiles "
    "para evitar que el ruido afecte a terceros?"
)

TOP_K = 5
CANDIDATE_K = TOP_K * 4
HOST = "127.0.0.1"
PORT = 15432
DATABASE = "tododerechovecino"
USERNAME = "tdv_admin"

pgpassfile = os.environ.get("PGPASSFILE")
if not pgpassfile or not os.path.isfile(pgpassfile):
    raise SystemExit(
        "ERROR: PGPASSFILE no está definido o no existe."
    )

client = boto3.client("bedrock-runtime", region_name="us-east-1")
vector = generate_embedding(client, QUESTION)

if len(vector) != DIMENSIONS:
    raise SystemExit(
        f"Dimensiones incorrectas: {len(vector)}; esperadas: {DIMENSIONS}"
    )

vector_sql = "[" + ",".join(str(float(x)) for x in vector) + "]"

sql = r"""
WITH candidatos AS (
    SELECT
        d.name AS documento,
        c.article AS articulo,
        c.legal_citation AS cita_legal,
        (e.embedding <=> :'vector'::vector) AS distancia,
        e.segment_index AS segmento,
        e.needs_review AS pendiente_revision,
        LEFT(e.segment_text, 350) AS fragmento,
        ts_rank_cd(
            to_tsvector('spanish', COALESCE(e.segment_text, '')),
            plainto_tsquery('spanish', :'question')
        ) AS relevancia_and,
        ts_rank_cd(
            to_tsvector('spanish', COALESCE(e.segment_text, '')),
            to_tsquery(
                'spanish',
                'ruido | exterior | terceros | emisiones | sonoras'
            )
        ) AS relevancia_or
    FROM legal_embeddings e
    JOIN legal_documents d ON d.id = e.document_id
    JOIN legal_chunks c
      ON c.id = e.legal_chunk_id
     AND c.document_id = e.document_id
    ORDER BY e.embedding <=> :'vector'::vector
    LIMIT :candidate_k
),
rankings AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY distancia ASC
        ) AS rango_vectorial,
        ROW_NUMBER() OVER (
            ORDER BY
                distancia - LEAST(relevancia_and, 1.0) * 0.08 ASC,
                distancia ASC
        ) AS rango_and,
        ROW_NUMBER() OVER (
            ORDER BY
                distancia - LEAST(relevancia_or, 1.0) * 0.08 ASC,
                distancia ASC
        ) AS rango_or
    FROM candidatos
)
SELECT COALESCE(
    json_agg(row_to_json(r) ORDER BY rango_vectorial),
    '[]'::json
)::text
FROM (
    SELECT
        documento,
        articulo,
        cita_legal,
        ROUND(distancia::numeric, 6) AS distancia,
        ROUND(relevancia_and::numeric, 6) AS score_and,
        ROUND(relevancia_or::numeric, 6) AS score_or,
        rango_vectorial,
        rango_and,
        rango_or,
        pendiente_revision,
        fragmento
    FROM rankings
    ORDER BY rango_vectorial
) r;
"""

input_psql = (
    f"\\set vector '{vector_sql}'\n"
    f"\\set question '{QUESTION.replace(chr(39), chr(39) * 2)}'\n"
    f"\\set candidate_k {CANDIDATE_K}\n"
    + sql
)

cmd = [
    "psql", "-X", "-w", "-A", "-t", "-q",
    "-h", HOST, "-p", str(PORT),
    "-U", USERNAME, "-d", DATABASE,
    "-v", "ON_ERROR_STOP=1",
]

result = subprocess.run(
    cmd,
    input=input_psql,
    capture_output=True,
    text=True,
    check=False,
)

if result.returncode != 0:
    raise SystemExit("ERROR PostgreSQL:\n" + result.stderr)

rows = json.loads(result.stdout.strip() or "[]")

print(f"\nCandidatos analizados: {len(rows)}")
print("Ranking comparativo: vectorial / AND / OR\n")

for row in sorted(rows, key=lambda x: x["rango_or"]):
    print(
        f"OR #{row['rango_or']:>2} | "
        f"AND #{row['rango_and']:>2} | "
        f"Vector #{row['rango_vectorial']:>2} | "
        f"AND score={row['score_and']} | "
        f"OR score={row['score_or']}"
    )
    print(f"  {row['cita_legal']}")
    print(f"  Pendiente de revisión: {row['pendiente_revision']}")
    print(f"  {row['fragmento']}\n")
