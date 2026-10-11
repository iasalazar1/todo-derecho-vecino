import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from generar_embeddings import (
    CONFIG_PATH,
    DIMENSIONS,
    MODEL_ID,
    ROOT,
    choose_sample,
    embedding_text,
    generate_embedding,
    load_json,
    read_chunks,
    resolve_chunks_path,
    split_text,
)

METADATA_FIELDS = [
    "tipo_documento",
    "titulo_completo",
    "jurisdiccion",
    "fecha_publicacion",
    "fecha_ultima_reforma",
    "estado_vigencia",
    "titulo",
    "capitulo",
    "seccion",
    "articulo",
    "fraccion",
    "contexto_superior",
    "tema_principal",
    "tipo_disposicion",
    "sujetos_obligados",
    "cita_legal",
    "fuente",
    "needs_review",
]


def record_key(record):
    return (
        record["source_file"],
        str(record["chunk_id"]),
        record["segment_index"],
        record["segment_count"],
    )


def load_completed(output_path):
    """Lee los segmentos guardados para permitir reanudar."""
    completed = set()

    if not output_path.exists():
        return completed

    with output_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                completed.add(record_key(record))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(
                    f"Registro JSONL inválido en línea {line_number}: {exc}"
                ) from exc

    return completed


def main():
    parser = argparse.ArgumentParser(
        description="Generación persistente y reanudable de embeddings legales."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Máximo de chunks para la prueba. Usa 0 para procesar todos.",
    )
    parser.add_argument(
    "--chunk-id",
    help="Procesa únicamente el chunk_id indicado.",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
    )
    parser.add_argument(
        "--output",
        default="salida/embeddings_prueba.jsonl",
        help="Archivo JSONL donde se guardarán los embeddings.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula el volumen de segmentación sin llamar a Bedrock.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda desde el archivo existente y omite segmentos completos.",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit no puede ser negativo.")

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    if output_path.exists() and not args.resume:
        raise ValueError(
            f"El archivo ya existe: {output_path}\n"
            "Usa --resume para continuar sin repetir segmentos, "
            "o especifica otro archivo de salida."
        )

    config = load_json(CONFIG_PATH)
    if not isinstance(config, list) or len(config) != 5:
        raise ValueError(
            "La configuración MVP debe contener exactamente "
            "los cinco instrumentos autorizados."
        )

    all_chunks = []
    seen_ids = set()

    for document in config:
        chunks_path = resolve_chunks_path(document["reviewed_path"])
        if not chunks_path.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo de chunks: {chunks_path}"
            )

        chunks = read_chunks(chunks_path)
        source_file = str(chunks_path.relative_to(ROOT))
        print(f"Leído: {source_file} ({len(chunks)} chunks)")

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                raise ValueError(f"Chunk sin chunk_id en {source_file}")

            unique_id = (source_file, str(chunk_id))
            if unique_id in seen_ids:
                raise ValueError(
                    f"chunk_id duplicado en {source_file}: {chunk_id}"
                )
            seen_ids.add(unique_id)

            if not str(chunk.get("texto") or "").strip():
                continue

            all_chunks.append({
                "chunk": chunk,
                "document_config": document,
                "source_file": source_file,
            })

    flattened = [
        {
            **item["chunk"],
            "_document_config": item["document_config"],
            "_source_path": item["document_config"]["reviewed_path"],
            "_source_file": item["source_file"],
        }
        for item in all_chunks
    ]

    if args.chunk_id:
        samples = [
            chunk for chunk in flattened
            if str(chunk.get("chunk_id")) == args.chunk_id
        ]
        if not samples:
            raise ValueError(
                f"No se encontró el chunk_id solicitado: {args.chunk_id}"
            )
    elif args.limit == 0:
        samples = flattened
    else:
        samples = choose_sample(flattened, args.limit)

    if args.dry_run:
        from collections import defaultdict

        total_chunks = len(samples)
        total_segments = 0
        max_original_chars = 0
        max_segment_chars = 0
        segments_by_document = defaultdict(int)
        large_chunks = []

        for chunk in samples:
            text = str(chunk.get("texto") or "")
            segments = split_text(text)
            source_file = chunk["_source_file"]

            total_segments += len(segments)
            segments_by_document[source_file] += len(segments)
            max_original_chars = max(max_original_chars, len(text))

            if len(text) > 45000:
                large_chunks.append(
                    (source_file, chunk["chunk_id"], len(text), len(segments))
                )

            for segment in segments:
                prepared = embedding_text(
                    chunk,
                    chunk["_document_config"],
                    text_override=segment,
                )
                max_segment_chars = max(max_segment_chars, len(prepared))

                if len(prepared) > 50000:
                    raise ValueError(
                        f"Texto preparado demasiado largo: {len(prepared)} "
                        f"caracteres; chunk={chunk['chunk_id']}"
                    )

        print("\n=== DIAGNÓSTICO DRY-RUN ===")
        print(f"Chunks seleccionados: {total_chunks}")
        print(f"Segmentos estimados: {total_segments}")
        print(f"Llamadas estimadas a Bedrock (sin reanudación): {total_segments}")
        print(f"Máximo de caracteres en un chunk original: {max_original_chars}")
        print(f"Máximo de caracteres en texto preparado: {max_segment_chars}")

        print("\nSegmentos estimados por documento:")
        for source_file, count in sorted(segments_by_document.items()):
            print(f"  {source_file}: {count}")

        print("\nChunks originales mayores de 45,000 caracteres:")
        for source_file, chunk_id, chars, count in large_chunks:
            print(
                f"  {source_file} | chunk={chunk_id} | "
                f"caracteres={chars} | segmentos={count}"
            )

        print("\nNo se invocó Bedrock ni se generaron embeddings.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = load_completed(output_path) if args.resume else set()


    print(f"\nInstrumentos autorizados: {len(config)}")
    print(f"Chunks seleccionados: {len(samples)}")
    print(f"Modelo: {MODEL_ID}")
    print(f"Región: {args.region}")
    print(f"Salida: {output_path}")
    print(f"Segmentos previamente guardados: {len(completed)}")
    print("Modo: persistencia local; no escribe en Aurora.\n")

    client = boto3.client("bedrock-runtime", region_name=args.region)
    generated = 0
    skipped = 0

    with output_path.open("a", encoding="utf-8") as out:
        for chunk in samples:
            document = chunk["_document_config"]
            source_file = chunk["_source_file"]
            original_text = str(chunk.get("texto") or "")
            segments = split_text(original_text)

            if not segments:
                continue

            chunk_id = chunk["chunk_id"]
            metadata = {
                field: chunk[field]
                for field in METADATA_FIELDS
                if field in chunk
            }

            for segment_index, segment in enumerate(segments, start=1):
                identity = {
                    "source_file": source_file,
                    "chunk_id": str(chunk_id),
                    "segment_index": segment_index,
                    "segment_count": len(segments),
                }
                key = record_key(identity)

                if key in completed:
                    skipped += 1
                    continue

                prepared_text = embedding_text(
                    chunk,
                    document,
                    text_override=segment,
                )

                if len(prepared_text) > 50000:
                    raise ValueError(
                        f"Texto preparado demasiado largo: "
                        f"{len(prepared_text)} caracteres; "
                        f"chunk={chunk_id}, segmento={segment_index}"
                    )

                try:
                    vector = generate_embedding(client, prepared_text)
                except (BotoCoreError, ClientError) as exc:
                    raise RuntimeError(
                        f"Falló Bedrock en {source_file}, "
                        f"chunk_id={chunk_id}, "
                        f"segmento={segment_index}/{len(segments)}. "
                        f"Los segmentos anteriores permanecen guardados. "
                        f"Detalle: {exc}"
                    ) from exc

                record = {
                    **identity,
                    "reviewed_path": document["reviewed_path"],
                    "document_title": document.get("titulo"),
                    "metadata": metadata,
                    "needs_review": chunk.get("needs_review"),
                    "segment_text": segment,
                    "embedding_model": MODEL_ID,
                    "dimensions": DIMENSIONS,
                    "embedding": vector,
                }

                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                completed.add(key)
                generated += 1

                print(
                    f"OK | chunk={chunk_id} | "
                    f"segmento={segment_index}/{len(segments)} | "
                    f"caracteres={len(prepared_text)} | "
                    f"dimensiones={len(vector)}"
                )

    print("\nProceso terminado.")
    print(f"Embeddings nuevos guardados: {generated}")
    print(f"Segmentos omitidos por estar guardados: {skipped}")
    print(f"Archivo: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except (
        BotoCoreError,
        ClientError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        RuntimeError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
