# todo-derecho-vecino
Una herramienta de acompañamiento legal para ciudadanos afectados por ilícitos en materia de uso de suelo. Este un sistema basado en un RAG-LLM que facilita la consulta de leyes, reglamentos y documentos de planeación urbana específicos para el ordenamiento del uso de suelo en la alcaldía Cuauhtémoc.

## Carga del corpus y embeddings en Aurora

`scripts/load_embeddings.py` valida los chunks configurados y un JSONL producido por `generar_embeddings_persistente.py`. Por defecto solo informa resultados; no conecta ni modifica Aurora. Requiere Python del entorno del proyecto y no añade dependencias.

Con Aurora disponible, el esquema inicializado y un túnel SSM activo en `127.0.0.1:15432`, primero valida el piloto:

```bash
./.venv/bin/python scripts/load_embeddings.py \
  --embeddings salida/embeddings_piloto_25bc7c1d8a1e.jsonl \
  --allow-incomplete
```

Para cargarlo, añade `--apply`. La conexión usa `tdv_admin`/`tododerechovecino` y el archivo PostgreSQL `.pgpass` (o `PGPASSFILE`), que debe tener permisos `0600`; nunca pases la contraseña en la línea de comandos. La carga piloto no borra embeddings existentes.

La carga completa requiere un JSONL con todos los segmentos del corpus. Genéralo primero en un archivo nuevo para no mezclarlo con pruebas anteriores:

```bash
./.venv/bin/python generar_embeddings_persistente.py \
  --limit 0 \
  --output salida/embeddings_mvp_completos.jsonl
```

Luego valida ese archivo sin `--allow-incomplete` y ejecútalo con `--apply`. La carga completa sincroniza chunks y embeddings de los documentos configurados dentro de una transacción; no elimina otros documentos de la base. Conserva los archivos fuente y el JSONL, porque Aurora DEV se puede destruir al apagar el ambiente.
