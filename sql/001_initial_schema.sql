-- Todo Derecho Vecino
-- Esquema inicial del corpus juridico y sus embeddings.
-- PostgreSQL / Aurora PostgreSQL con pgvector.
--
-- Este archivo crea la estructura de datos.
-- NO carga documentos ni embeddings.
-- NO elimina tablas ni datos existentes.

BEGIN;

-- ============================================================
-- 1. Extension vectorial
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. Documentos juridicos
-- Un registro por instrumento juridico del corpus.
-- ============================================================

CREATE TABLE IF NOT EXISTS legal_documents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    document_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    document_type TEXT,
    authority TEXT,
    jurisdiction TEXT,

    source_url TEXT,
    publication_date DATE,
    reform_date DATE,
    version TEXT,
    validity_status TEXT,

    -- Claves de los archivos originales almacenados en S3.
    reviewed_text_s3_key TEXT,
    chunks_s3_key TEXT,

    document_hash TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT legal_documents_document_key_not_empty
        CHECK (length(trim(document_key)) > 0),

    CONSTRAINT legal_documents_name_not_empty
        CHECK (length(trim(name)) > 0)
);

-- ============================================================
-- 3. Fragmentos juridicos originales
-- Un registro por chunk del procesador documental.
-- ============================================================

CREATE TABLE IF NOT EXISTS legal_chunks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    document_id BIGINT NOT NULL
        REFERENCES legal_documents(id)
        ON DELETE CASCADE,

    -- Identificador generado por legal_document_processor.py.
    chunk_id VARCHAR(12) NOT NULL,

    -- Posicion del fragmento en el archivo original.
    -- La carga de datos debe asignarla de forma determinista.
    chunk_index INTEGER NOT NULL,

    title TEXT,
    chapter TEXT,
    section TEXT,
    article TEXT,
    fraction TEXT,

    legal_citation TEXT,
    chunk_text TEXT NOT NULL,

    -- Metadatos juridicos del fragmento en formato flexible.
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT legal_chunks_chunk_index_positive
        CHECK (chunk_index >= 1),

    CONSTRAINT legal_chunks_chunk_id_not_empty
        CHECK (length(trim(chunk_id)) > 0),

    CONSTRAINT legal_chunks_text_not_empty
        CHECK (length(trim(chunk_text)) > 0),

    CONSTRAINT legal_chunks_document_index_unique
        UNIQUE (document_id, chunk_index),

    -- Necesaria para que embeddings pueda verificar que
    -- el fragmento pertenece al mismo documento.
    CONSTRAINT legal_chunks_id_document_unique
        UNIQUE (id, document_id)
);

-- ============================================================
-- 4. Segmentos vectorizados
-- Un fragmento puede generar uno o varios segmentos.
-- ============================================================

CREATE TABLE IF NOT EXISTS legal_embeddings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    legal_chunk_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,

    segment_index INTEGER NOT NULL,
    segment_count INTEGER NOT NULL,

    segment_text TEXT NOT NULL,

    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL,
    dimensions INTEGER NOT NULL DEFAULT 1024,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT legal_embeddings_chunk_document_fk
        FOREIGN KEY (legal_chunk_id, document_id)
        REFERENCES legal_chunks(id, document_id)
        ON DELETE CASCADE,

    CONSTRAINT legal_embeddings_segment_index_positive
        CHECK (segment_index >= 1),

    CONSTRAINT legal_embeddings_segment_count_valid
        CHECK (
            segment_count >= 1
            AND segment_index <= segment_count
        ),

    CONSTRAINT legal_embeddings_dimensions_valid
        CHECK (dimensions = 1024),

    CONSTRAINT legal_embeddings_text_not_empty
        CHECK (length(trim(segment_text)) > 0),

    CONSTRAINT legal_embeddings_model_not_empty
        CHECK (length(trim(embedding_model)) > 0),

    CONSTRAINT legal_embeddings_chunk_segment_unique
        UNIQUE (legal_chunk_id, segment_index)
);

-- ============================================================
-- 5. Indices para consultas y recuperacion semantica
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_legal_chunks_document
    ON legal_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_legal_chunks_article
    ON legal_chunks (article);

CREATE INDEX IF NOT EXISTS idx_legal_chunks_metadata
    ON legal_chunks USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_legal_embeddings_document
    ON legal_embeddings (document_id);

CREATE INDEX IF NOT EXISTS idx_legal_embeddings_metadata
    ON legal_embeddings USING GIN (metadata);

-- ============================================================
-- 6. Descripcion del esquema
-- ============================================================

COMMENT ON TABLE legal_documents IS
    'Catalogo de instrumentos juridicos del corpus MVP.';

COMMENT ON TABLE legal_chunks IS
    'Fragmentos juridicos originales con su contexto y metadatos.';

COMMENT ON TABLE legal_embeddings IS
    'Segmentos de texto vectorizados con embeddings de 1024 dimensiones.';

COMMENT ON COLUMN legal_chunks.chunk_id IS
    'Identificador generado por el procesador; no se asume unicidad por documento.';

COMMENT ON COLUMN legal_chunks.chunk_index IS
    'Posicion determinista del fragmento en el archivo de origen.';

COMMENT ON COLUMN legal_embeddings.segment_index IS
    'Posicion del segmento dentro de su fragmento original.';

COMMENT ON COLUMN legal_embeddings.embedding IS
    'Vector generado por el modelo de embeddings indicado en embedding_model.';

COMMIT;
