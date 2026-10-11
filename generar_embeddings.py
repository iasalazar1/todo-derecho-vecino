import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "documentos_config_mvp.json"
MODEL_ID = "amazon.titan-embed-text-v2:0"
DIMENSIONS = 1024
MAX_SEGMENT_CHARS = 8000

# Metadatos útiles para recuperar disposiciones legales por similitud.
METADATA_FIELDS = [
    "jurisdiccion",
    "titulo",
    "capitulo",
    "seccion",
    "articulo",
    "fraccion",
    "contexto_superior",
    "tema_principal",
    "cita_legal",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_chunks_path(reviewed_path):
    # Ejemplo: documento_reviewed.txt -> documento_reviewed_chunks.json
    reviewed_stem = Path(reviewed_path).stem
    return ROOT / "leyes_cdmx" / f"{reviewed_stem}_chunks.json"


def read_chunks(path):
    data = load_json(path)

    if isinstance(data, list):
        chunks = data
    elif isinstance(data, dict):
        chunks = data.get("chunks")
        if not isinstance(chunks, list):
            raise ValueError(
                f"Formato JSON no reconocido en {path}: "
                "se esperaba una lista o una clave 'chunks'."
            )
    else:
        raise ValueError(f"Formato JSON no reconocido en {path}")

    return chunks


def embedding_text(chunk, document_config, text_override=None):
    parts = []

    # Usa los metadatos existentes; no inventa valores ausentes.
    document_title = (
        chunk.get("titulo_completo")
        or document_config.get("titulo")
    )
    if document_title:
        parts.append(f"Documento: {document_title}")

    document_type = (
        chunk.get("tipo_documento")
        or document_config.get("tipo_documento")
    )
    if document_type:
        parts.append(f"Tipo de documento: {document_type}")

    for field in METADATA_FIELDS:
        value = chunk.get(field)
        if value is not None and str(value).strip():
            # Evita repetir el título si coincide con titulo_completo.
            if field == "titulo" and str(value).strip() == str(document_title).strip():
                continue
            parts.append(f"{field}: {str(value).strip()}")

    text = (
        chunk.get("texto")
        if text_override is None
        else text_override
    )
    if text is not None and str(text).strip():
        parts.append(f"Texto jurídico:\n{str(text)}")

    return "\n".join(parts).strip()


def split_text(text, max_chars=MAX_SEGMENT_CHARS):
    """
    Divide el texto en segmentos contiguos sin perder ni modificar
    caracteres. Prefiere saltos de línea y espacios como límites.
    """
    if not text:
        return []

    segments = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            # Busca un límite natural en el último 40 % del segmento.
            search_start = start + int(max_chars * 0.60)
            newline = text.rfind("\n", search_start, end)

            if newline > start:
                end = newline + 1
            else:
                space = text.rfind(" ", search_start, end)
                if space > start:
                    end = space + 1

        segments.append(text[start:end])
        start = end

    # Garantiza que la segmentación no pierda contenido.
    if "".join(segments) != text:
        raise ValueError("La segmentación alteró el texto original.")

    return segments

def choose_sample(chunks, limit):
    """Selecciona fragmentos cortos, intermedios y largos para la prueba."""
    usable = [
        c for c in chunks
        if isinstance(c, dict) and str(c.get("texto", "")).strip()
    ]
    if len(usable) <= limit:
        return usable

    by_length = sorted(usable, key=lambda c: len(str(c.get("texto", ""))))
    positions = [0, len(by_length) // 2, len(by_length) - 1]

    selected = []
    for pos in positions:
        candidate = by_length[pos]
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= limit:
            break

    # Si limit es mayor que tres, completa con fragmentos distribuidos.
    if len(selected) < limit:
        step = max(1, len(by_length) // limit)
        for candidate in by_length[::step]:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) >= limit:
                break

    return selected[:limit]


def generate_embedding(client, text):
    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "inputText": text,
            "dimensions": DIMENSIONS,
            "normalize": True,
        }),
    )
    body = json.loads(response["body"].read())
    vector = body.get("embedding")

    if not isinstance(vector, list):
        raise ValueError("Bedrock no devolvió una lista en 'embedding'.")
    if len(vector) != DIMENSIONS:
        raise ValueError(
            f"Dimensión inesperada: {len(vector)}; "
            f"se esperaban {DIMENSIONS}."
        )

    return vector


def main():
    parser = argparse.ArgumentParser(
        description="Prueba controlada de embeddings legales con Amazon Titan V2."
    )
    parser.add_argument(
        "--limit", type=int, default=3,
        help="Número máximo de chunks para la prueba (predeterminado: 3).",
    )
    parser.add_argument(
        "--region", default=os.getenv("AWS_REGION", "us-east-1"),
        help="Región de AWS (predeterminada: us-east-1).",
    )
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit debe ser al menos 1.")

    config = load_json(CONFIG_PATH)
    if not isinstance(config, list):
        raise ValueError("La configuración MVP debe ser una lista JSON.")

    all_chunks = []
    seen_ids = set()

    for document in config:
        chunks_path = resolve_chunks_path(document["reviewed_path"])
        if not chunks_path.is_file():
            raise FileNotFoundError(
                f"No se encontró el JSON de chunks esperado: {chunks_path}\n"
                "Verifica el nombre real del archivo; no se generará "
                "ni modificará ningún corpus automáticamente."
            )

        chunks = read_chunks(chunks_path)
        print(f"Leído: {chunks_path.relative_to(ROOT)} ({len(chunks)} chunks)")

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            # Adjunta la configuración como contexto, sin alterar el chunk.
            record = {
                "chunk": chunk,
                "document_config": document,
            }
            chunk_id = chunk.get("chunk_id")
            unique_key = (str(chunks_path), str(chunk_id))

            if unique_key in seen_ids:
                raise ValueError(
                    f"chunk_id duplicado en el mismo archivo: {chunk_id}"
                )
            seen_ids.add(unique_key)
            all_chunks.append(record)

    # Selecciona ejemplos de todo el corpus autorizado, no solo de una ley.
    flattened = [
        {
            **record["chunk"],
            "_document_config": record["document_config"],
            "_source_path": record["document_config"]["reviewed_path"],
        }
        for record in all_chunks
        if str(record["chunk"].get("texto", "")).strip()
    ]
    samples = choose_sample(flattened, args.limit)

    if not samples:
        raise ValueError("No se encontraron chunks con texto no vacío.")

    client = boto3.client("bedrock-runtime", region_name=args.region)

    print(f"\nModelo: {MODEL_ID}")
    print(f"Región: {args.region}")
    print(f"Chunks seleccionados: {len(samples)}")
    print("Modo: prueba; no guarda vectores ni escribe en la base de datos.\n")

    for index, chunk in enumerate(samples, start=1):
        source_config = chunk["_document_config"]
        original_text = str(chunk.get("texto") or "")
        segments = split_text(original_text)

        if not segments:
            print(
                f"[OMITIDO] Chunk {chunk.get('chunk_id')} "
                "sin texto para embedding"
            )
            continue

        print(f"\nPrueba {index}:")
        print(f"  Documento: {source_config.get('titulo', 'Sin título')}")
        print(f"  chunk_id original: {chunk.get('chunk_id')}")
        print(f"  Caracteres originales: {len(original_text)}")
        print(f"  Segmentos generados: {len(segments)}")

        for segment_index, segment in enumerate(segments, start=1):
            text = embedding_text(
                chunk,
                source_config,
                text_override=segment,
            )

            if not text:
                continue

            if len(text) > 50000:
                raise ValueError(
                    f"El texto preparado excede el límite de Titan: "
                    f"{len(text)} caracteres; chunk_id="
                    f"{chunk.get('chunk_id')}, segmento={segment_index}"
                )

            vector = generate_embedding(client, text)

            print(
                f"  Segmento {segment_index}/{len(segments)}: OK"
            )
            print(f"    Caracteres del segmento legal: {len(segment)}")
            print(f"    Caracteres preparados: {len(text)}")
            print(f"    Dimensiones del vector: {len(vector)}")

        print(f"  needs_review: {chunk.get('needs_review', 'No disponible')}")


if __name__ == "__main__":
    try:
        main()
    except (BotoCoreError, ClientError) as exc:
        print(f"Error de AWS/Bedrock: {exc}", file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
