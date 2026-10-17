#!/usr/bin/env python3
"""Load the approved MVP corpus and its embeddings into Aurora PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generar_embeddings import (
    CONFIG_PATH,
    DIMENSIONS,
    MODEL_ID,
    ROOT,
    load_json,
    read_chunks,
    resolve_chunks_path,
    split_text,
)


@dataclass(frozen=True)
class CorpusDocument:
    document_key: str
    name: str
    document_type: str | None
    authority: str | None
    jurisdiction: str | None
    source_url: str | None
    publication_date: str | None
    reform_date: str | None
    version: str | None
    validity_status: str | None
    document_hash: str


@dataclass(frozen=True)
class CorpusChunk:
    source_file: str
    chunk_id: str
    chunk_index: int
    title: str | None
    chapter: str | None
    section: str | None
    article: str | None
    fraction: str | None
    legal_citation: str | None
    chunk_text: str
    metadata: str
    needs_review: bool


@dataclass(frozen=True)
class CorpusEmbedding:
    source_file: str
    chunk_id: str
    chunk_index: int
    segment_index: int
    segment_count: int
    segment_text: str
    embedding: str
    embedding_model: str
    dimensions: int
    metadata: str
    needs_review: bool


def optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"El campo {field} debe ser texto o null.")
    return value or None


def optional_date(value: Any, field: str) -> str | None:
    text = optional_text(value, field)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"Fecha inválida en {field}: {text!r}.") from exc


def require_review_flag(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context}: needs_review debe ser booleano.")
    return value


def load_corpus(
    config_path: Path,
) -> tuple[list[CorpusDocument], list[CorpusChunk], dict[tuple[str, str], int]]:
    config = load_json(config_path)
    if not isinstance(config, list) or not config:
        raise ValueError(f"{config_path}: se esperaba una lista JSON no vacía.")

    documents: list[CorpusDocument] = []
    chunks: list[CorpusChunk] = []
    chunk_indexes: dict[tuple[str, str], int] = {}
    seen_document_keys: set[str] = set()

    for document_config in config:
        if not isinstance(document_config, dict):
            raise ValueError("Cada entrada de documentos_config_mvp.json debe ser objeto.")
        reviewed_path = document_config.get("reviewed_path")
        if not isinstance(reviewed_path, str) or not reviewed_path:
            raise ValueError("Cada documento debe definir reviewed_path.")

        chunks_path = resolve_chunks_path(reviewed_path)
        if not chunks_path.is_file():
            raise FileNotFoundError(f"No se encontró el JSON de chunks: {chunks_path}")
        document_key = chunks_path.relative_to(ROOT).as_posix()
        if document_key in seen_document_keys:
            raise ValueError(f"Documento duplicado en la configuración: {document_key}")
        seen_document_keys.add(document_key)

        source_chunks = read_chunks(chunks_path)
        if not source_chunks:
            raise ValueError(f"El documento no contiene chunks: {document_key}")

        first_chunk = next(
            (chunk for chunk in source_chunks if isinstance(chunk, dict)),
            None,
        )
        if first_chunk is None:
            raise ValueError(f"No hay chunks válidos en {document_key}.")

        document = CorpusDocument(
            document_key=document_key,
            name=optional_text(document_config.get("titulo"), "titulo") or document_key,
            document_type=optional_text(
                document_config.get("tipo_documento")
                or first_chunk.get("tipo_documento"),
                "tipo_documento",
            ),
            authority=None,
            jurisdiction=optional_text(first_chunk.get("jurisdiccion"), "jurisdiccion"),
            source_url=optional_text(
                document_config.get("fuente") or first_chunk.get("fuente"),
                "fuente",
            ),
            publication_date=optional_date(
                first_chunk.get("fecha_publicacion"),
                "fecha_publicacion",
            ),
            reform_date=optional_date(
                first_chunk.get("fecha_ultima_reforma"),
                "fecha_ultima_reforma",
            ),
            version=None,
            validity_status=optional_text(
                first_chunk.get("estado_vigencia"),
                "estado_vigencia",
            ),
            document_hash=hashlib.sha256(chunks_path.read_bytes()).hexdigest(),
        )
        documents.append(document)

        for chunk_index, source_chunk in enumerate(source_chunks, start=1):
            if not isinstance(source_chunk, dict):
                raise ValueError(
                    f"Chunk no es un objeto en {document_key}, posición {chunk_index}."
                )
            chunk_id = source_chunk.get("chunk_id")
            text = source_chunk.get("texto")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(
                    f"chunk_id vacío o inválido en {document_key}, posición {chunk_index}."
                )
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"Texto vacío o inválido en {document_key}, chunk {chunk_id}."
                )

            identity = (document_key, chunk_id)
            if identity in chunk_indexes:
                raise ValueError(
                    f"chunk_id duplicado en {document_key}: {chunk_id}."
                )
            chunk_indexes[identity] = chunk_index

            metadata = json.dumps(
                source_chunk,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            chunks.append(
                CorpusChunk(
                    source_file=document_key,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    title=optional_text(source_chunk.get("titulo"), "titulo"),
                    chapter=optional_text(source_chunk.get("capitulo"), "capitulo"),
                    section=optional_text(source_chunk.get("seccion"), "seccion"),
                    article=optional_text(source_chunk.get("articulo"), "articulo"),
                    fraction=optional_text(source_chunk.get("fraccion"), "fraccion"),
                    legal_citation=optional_text(
                        source_chunk.get("cita_legal"),
                        "cita_legal",
                    ),
                    chunk_text=text,
                    metadata=metadata,
                    needs_review=require_review_flag(
                        source_chunk.get("needs_review"),
                        f"{document_key}, chunk {chunk_id}",
                    ),
                )
            )

    return documents, chunks, chunk_indexes


def load_embeddings(
    embeddings_path: Path,
    chunk_indexes: dict[tuple[str, str], int],
    config_path: Path,
) -> tuple[list[CorpusEmbedding], set[tuple[str, str, int]]]:
    expected_segments: set[tuple[str, str, int]] = set()
    expected_text: dict[tuple[str, str, int], tuple[int, str]] = {}

    config = load_json(config_path)
    for document_config in config:
        source_file = resolve_chunks_path(document_config["reviewed_path"]).relative_to(
            ROOT
        ).as_posix()
        for chunk in read_chunks(resolve_chunks_path(document_config["reviewed_path"])):
            text = chunk["texto"]
            for segment_index, segment_text in enumerate(split_text(text), start=1):
                key = (source_file, str(chunk["chunk_id"]), segment_index)
                expected_segments.add(key)
                expected_text[key] = (len(split_text(text)), segment_text)

    embeddings: list[CorpusEmbedding] = []
    seen: set[tuple[str, str, int]] = set()
    with embeddings_path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSONL inválido en {embeddings_path}, línea {line_number}: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(f"Línea {line_number}: se esperaba un objeto JSON.")

            source_file = record.get("source_file")
            chunk_id = record.get("chunk_id")
            if not isinstance(source_file, str) or not isinstance(chunk_id, str):
                raise ValueError(
                    f"Línea {line_number}: source_file y chunk_id deben ser texto."
                )
            identity = (source_file, chunk_id)
            if identity not in chunk_indexes:
                raise ValueError(
                    f"Línea {line_number}: chunk no incluido en el corpus aprobado: "
                    f"{source_file} / {chunk_id}."
                )

            segment_index = record.get("segment_index")
            segment_count = record.get("segment_count")
            if (
                not isinstance(segment_index, int)
                or isinstance(segment_index, bool)
                or segment_index < 1
            ):
                raise ValueError(f"Línea {line_number}: segment_index inválido.")
            if (
                not isinstance(segment_count, int)
                or isinstance(segment_count, bool)
                or segment_count < 1
            ):
                raise ValueError(f"Línea {line_number}: segment_count inválido.")
            key = (source_file, chunk_id, segment_index)
            if key not in expected_segments:
                raise ValueError(
                    f"Línea {line_number}: segmento inexistente para "
                    f"{source_file} / {chunk_id} / {segment_index}."
                )
            expected_count, expected_segment_text = expected_text[key]
            if segment_count != expected_count:
                raise ValueError(
                    f"Línea {line_number}: segment_count={segment_count}; "
                    f"se esperaba {expected_count}."
                )
            if key in seen:
                raise ValueError(f"Línea {line_number}: segmento duplicado {key}.")

            segment_text = record.get("segment_text")
            if segment_text != expected_segment_text:
                raise ValueError(
                    f"Línea {line_number}: el texto del segmento no coincide "
                    "con el corpus fuente."
                )
            if record.get("embedding_model") != MODEL_ID:
                raise ValueError(
                    f"Línea {line_number}: modelo inesperado "
                    f"{record.get('embedding_model')!r}; se esperaba {MODEL_ID!r}."
                )
            vector = record.get("embedding")
            if (
                not isinstance(vector, list)
                or len(vector) != DIMENSIONS
                or any(
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    for value in vector
                )
            ):
                raise ValueError(
                    f"Línea {line_number}: embedding inválido; se esperan "
                    f"{DIMENSIONS} números finitos."
                )
            if record.get("dimensions") != DIMENSIONS:
                raise ValueError(
                    f"Línea {line_number}: dimensions debe ser {DIMENSIONS}."
                )

            metadata = record.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError(f"Línea {line_number}: metadata debe ser objeto.")
            embedding_text = "[" + ",".join(format(value, ".9g") for value in vector) + "]"

            embeddings.append(
                CorpusEmbedding(
                    source_file=source_file,
                    chunk_id=chunk_id,
                    chunk_index=chunk_indexes[identity],
                    segment_index=segment_index,
                    segment_count=segment_count,
                    segment_text=segment_text,
                    embedding=embedding_text,
                    embedding_model=MODEL_ID,
                    dimensions=DIMENSIONS,
                    metadata=json.dumps(
                        metadata,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    needs_review=require_review_flag(
                        record.get("needs_review"),
                        f"{embeddings_path}, línea {line_number}",
                    ),
                )
            )
            seen.add(key)

    missing = expected_segments - seen
    extra = seen - expected_segments
    if extra:
        raise ValueError(f"El JSONL contiene segmentos ajenos al corpus: {sorted(extra)[:3]}")
    return embeddings, missing


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_csv(path: Path, rows: Iterable[Iterable[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerows(
            [csv_value(value) for value in row]
            for row in rows
        )


def build_sql(directory: Path, sync_snapshot: bool) -> Path:
    copy_commands = []
    for table in ("documents", "chunks", "embeddings"):
        csv_path = (directory / f"{table}.csv").as_posix().replace("'", "''")
        copy_commands.append(
            f"\\copy stage_{table} FROM '{csv_path}' WITH (FORMAT csv, NULL '')"
        )
    sync_sql = ""
    sync_chunks_sql = ""
    if sync_snapshot:
        sync_sql = """
DELETE FROM legal_embeddings AS e
USING legal_chunks AS c, legal_documents AS d
WHERE e.legal_chunk_id = c.id
  AND e.document_id = d.id
  AND d.document_key IN (SELECT document_key FROM stage_documents)
  AND NOT EXISTS (
      SELECT 1
      FROM stage_chunks AS sc
      JOIN stage_embeddings AS se
        ON se.source_file = sc.source_file
       AND se.chunk_index = sc.chunk_index
      WHERE sc.source_file = d.document_key
        AND sc.chunk_id = c.chunk_id
        AND sc.chunk_index = c.chunk_index
        AND se.segment_index = e.segment_index
        AND se.segment_count = e.segment_count
  );
"""
        sync_chunks_sql = """
DELETE FROM legal_chunks AS c
USING legal_documents AS d
WHERE c.document_id = d.id
  AND d.document_key IN (SELECT document_key FROM stage_documents)
  AND NOT EXISTS (
      SELECT 1
      FROM stage_chunks AS s
      WHERE s.source_file = d.document_key
        AND s.chunk_index = c.chunk_index
  );
"""
    else:
        sync_chunks_sql = """
DO $pilot$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM stage_chunks AS s
        JOIN legal_documents AS d ON d.document_key = s.source_file
        JOIN legal_chunks AS c
          ON c.document_id = d.id
         AND c.chunk_index = s.chunk_index
        WHERE c.chunk_id <> s.chunk_id
           OR c.chunk_text <> s.chunk_text
    ) THEN
        RAISE EXCEPTION
            'El corpus existente difiere del piloto. Usa la carga completa para sincronizar.';
    END IF;
END
$pilot$;
"""
    sql = f"""\
BEGIN;

CREATE TEMP TABLE stage_documents (
    document_key text PRIMARY KEY,
    name text NOT NULL,
    document_type text,
    authority text,
    jurisdiction text,
    source_url text,
    publication_date date,
    reform_date date,
    version text,
    validity_status text,
    document_hash text NOT NULL
) ON COMMIT DROP;

CREATE TEMP TABLE stage_chunks (
    source_file text NOT NULL,
    chunk_id text NOT NULL,
    chunk_index integer NOT NULL,
    title text,
    chapter text,
    section text,
    article text,
    fraction text,
    legal_citation text,
    chunk_text text NOT NULL,
    metadata jsonb NOT NULL,
    needs_review boolean NOT NULL,
    PRIMARY KEY (source_file, chunk_index),
    UNIQUE (source_file, chunk_id)
) ON COMMIT DROP;

CREATE TEMP TABLE stage_embeddings (
    source_file text NOT NULL,
    chunk_id text NOT NULL,
    chunk_index integer NOT NULL,
    segment_index integer NOT NULL,
    segment_count integer NOT NULL,
    segment_text text NOT NULL,
    embedding_text text NOT NULL,
    embedding_model text NOT NULL,
    dimensions integer NOT NULL,
    metadata jsonb NOT NULL,
    needs_review boolean NOT NULL,
    PRIMARY KEY (source_file, chunk_index, segment_index)
) ON COMMIT DROP;

{chr(10).join(copy_commands)}

INSERT INTO legal_documents (
    document_key, name, document_type, authority, jurisdiction, source_url,
    publication_date, reform_date, version, validity_status, document_hash
)
SELECT document_key, name, document_type, authority, jurisdiction, source_url,
       publication_date, reform_date, version, validity_status, document_hash
FROM stage_documents
ON CONFLICT (document_key) DO UPDATE SET
    name = EXCLUDED.name,
    document_type = EXCLUDED.document_type,
    authority = EXCLUDED.authority,
    jurisdiction = EXCLUDED.jurisdiction,
    source_url = EXCLUDED.source_url,
    publication_date = EXCLUDED.publication_date,
    reform_date = EXCLUDED.reform_date,
    version = EXCLUDED.version,
    validity_status = EXCLUDED.validity_status,
    document_hash = EXCLUDED.document_hash,
    updated_at = NOW();

{sync_sql}

{sync_chunks_sql}

INSERT INTO legal_chunks (
    document_id, chunk_id, chunk_index, title, chapter, section, article,
    fraction, legal_citation, chunk_text, metadata, needs_review
)
SELECT d.id, s.chunk_id, s.chunk_index, s.title, s.chapter, s.section,
       s.article, s.fraction, s.legal_citation, s.chunk_text, s.metadata,
       s.needs_review
FROM stage_chunks AS s
JOIN legal_documents AS d ON d.document_key = s.source_file
ON CONFLICT (document_id, chunk_index) DO UPDATE SET
    chunk_id = EXCLUDED.chunk_id,
    title = EXCLUDED.title,
    chapter = EXCLUDED.chapter,
    section = EXCLUDED.section,
    article = EXCLUDED.article,
    fraction = EXCLUDED.fraction,
    legal_citation = EXCLUDED.legal_citation,
    chunk_text = EXCLUDED.chunk_text,
    metadata = EXCLUDED.metadata,
    needs_review = EXCLUDED.needs_review;

INSERT INTO legal_embeddings (
    legal_chunk_id, document_id, segment_index, segment_count, segment_text,
    embedding, embedding_model, dimensions, metadata, needs_review
)
SELECT c.id, d.id, s.segment_index, s.segment_count, s.segment_text,
       s.embedding_text::vector, s.embedding_model, s.dimensions, s.metadata,
       s.needs_review
FROM stage_embeddings AS s
JOIN legal_documents AS d ON d.document_key = s.source_file
JOIN legal_chunks AS c
  ON c.document_id = d.id
 AND c.chunk_id = s.chunk_id
 AND c.chunk_index = s.chunk_index
ON CONFLICT (legal_chunk_id, segment_index) DO UPDATE SET
    segment_count = EXCLUDED.segment_count,
    segment_text = EXCLUDED.segment_text,
    embedding = EXCLUDED.embedding,
    embedding_model = EXCLUDED.embedding_model,
    dimensions = EXCLUDED.dimensions,
    metadata = EXCLUDED.metadata,
    needs_review = EXCLUDED.needs_review;

SELECT
    (SELECT count(*) FROM legal_documents
      WHERE document_key IN (SELECT document_key FROM stage_documents))
        AS documentos_corpus,
    (SELECT count(*) FROM legal_chunks c
      JOIN legal_documents d ON d.id = c.document_id
      WHERE d.document_key IN (SELECT document_key FROM stage_documents))
        AS chunks_corpus,
    (SELECT count(*) FROM legal_embeddings e
      JOIN legal_documents d ON d.id = e.document_id
      WHERE d.document_key IN (SELECT document_key FROM stage_documents))
        AS embeddings_corpus;

COMMIT;
"""
    sql_path = directory / "load_corpus.sql"
    sql_path.write_text(sql, encoding="utf-8")
    return sql_path


def run_psql(sql_path: Path, args: argparse.Namespace) -> None:
    if not shutil.which(args.psql):
        raise FileNotFoundError(f"No se encontró el cliente PostgreSQL: {args.psql}")
    passfile = Path(
        os.environ.get("PGPASSFILE", str(Path.home() / ".pgpass"))
    ).expanduser()
    if not passfile.is_file():
        raise ValueError(
            "No se encontró el archivo de credenciales PostgreSQL. "
            "Configura PGPASSFILE (permisos 0600); no pases la contraseña como argumento."
        )
    if passfile.stat().st_mode & 0o077:
        raise ValueError(
            f"El archivo {passfile} debe tener permisos 0600 para usarlo con PostgreSQL."
        )

    command = [
        args.psql,
        "-X",
        "-w",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.username,
        "-d",
        args.database,
        "-f",
        str(sql_path),
    ]
    environment = os.environ.copy()
    environment["PGPASSFILE"] = str(passfile.resolve())
    subprocess.run(command, check=True, cwd=ROOT, env=environment)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida e ingiere el corpus MVP y sus embeddings. "
            "Solo escribe en Aurora cuando se indica --apply."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Configuración del corpus MVP.",
    )
    parser.add_argument(
        "--embeddings",
        type=Path,
        required=True,
        help="JSONL persistente generado por generar_embeddings_persistente.py.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Permite un piloto parcial; no elimina embeddings existentes.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta la carga transaccional mediante psql.",
    )
    parser.add_argument("--psql", default="psql")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", default="tododerechovecino")
    parser.add_argument("--username", default="tdv_admin")
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    embeddings_path = (
        args.embeddings
        if args.embeddings.is_absolute()
        else ROOT / args.embeddings
    )
    if not embeddings_path.is_file():
        raise FileNotFoundError(f"No se encontró el JSONL: {embeddings_path}")

    documents, chunks, chunk_indexes = load_corpus(config_path)
    embeddings, missing = load_embeddings(
        embeddings_path,
        chunk_indexes,
        config_path,
    )
    if missing and not args.allow_incomplete:
        examples = sorted(missing)[:5]
        raise ValueError(
            f"Faltan {len(missing)} de los segmentos esperados. "
            "Usa --allow-incomplete solo para una carga piloto. "
            f"Ejemplos faltantes: {examples}"
        )

    expected = len(missing) + len(embeddings)
    print(f"Documentos: {len(documents)}")
    print(f"Chunks fuente: {len(chunks)}")
    print(f"Embeddings en JSONL: {len(embeddings)}")
    print(f"Segmentos esperados: {expected}")
    print(f"Segmentos faltantes: {len(missing)}")
    print(f"needs_review=true en chunks: {sum(c.needs_review for c in chunks)}")
    print(f"needs_review=true en embeddings: {sum(e.needs_review for e in embeddings)}")

    if not args.apply:
        print("\nValidación terminada; no se conectó a PostgreSQL ni se modificó Aurora.")
        return 0

    with tempfile.TemporaryDirectory(prefix="tdv-loader-") as temp_name:
        directory = Path(temp_name)
        write_csv(
            directory / "documents.csv",
            (
                (
                    document.document_key,
                    document.name,
                    document.document_type,
                    document.authority,
                    document.jurisdiction,
                    document.source_url,
                    document.publication_date,
                    document.reform_date,
                    document.version,
                    document.validity_status,
                    document.document_hash,
                )
                for document in documents
            ),
        )
        write_csv(
            directory / "chunks.csv",
            (
                (
                    chunk.source_file,
                    chunk.chunk_id,
                    chunk.chunk_index,
                    chunk.title,
                    chunk.chapter,
                    chunk.section,
                    chunk.article,
                    chunk.fraction,
                    chunk.legal_citation,
                    chunk.chunk_text,
                    chunk.metadata,
                    chunk.needs_review,
                )
                for chunk in chunks
            ),
        )
        write_csv(
            directory / "embeddings.csv",
            (
                (
                    embedding.source_file,
                    embedding.chunk_id,
                    embedding.chunk_index,
                    embedding.segment_index,
                    embedding.segment_count,
                    embedding.segment_text,
                    embedding.embedding,
                    embedding.embedding_model,
                    embedding.dimensions,
                    embedding.metadata,
                    embedding.needs_review,
                )
                for embedding in embeddings
            ),
        )
        sql_path = build_sql(directory, sync_snapshot=not args.allow_incomplete)
        print(
            "\nModo de carga: "
            + (
                "piloto incremental (no elimina datos existentes)"
                if args.allow_incomplete
                else "sincronización completa del corpus configurado"
            )
        )
        run_psql(sql_path, args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
