# Diseño conceptual del recuperador híbrido para el PPCU Hipódromo

## 1. Objetivo y límites

Proponer cómo combinar búsqueda semántica en `legal_embeddings` con consultas SQL sobre datos estructurados del PPCU y presentar sus evidencias al generador conservando procedencia y revisión. No se modifica `retriever.py`, `answer_question()`, el generador, Lambda, JSON, SQL o AWS.

## 2. Diagnóstico del recuperador actual

### Recuperación semántica (`retriever.retrieve`)

En `retriever.py`, `retrieve()`:

1. valida la pregunta y `top_k`;
2. crea un embedding de la pregunta mediante `generate_embedding`;
3. consulta `legal_embeddings`, enlazando con `legal_documents` y `legal_chunks`;
4. obtiene candidatos por distancia vectorial `<=>`, limita candidatos a `top_k * 4`, y reordena con una puntuación que combina distancia y `ts_rank_cd` de texto en español;
5. devuelve fragmento, nombre del documento, artículo/cita, segmento, distancia y `pendiente_revision`.

El modo Aurora usa `psycopg`, credenciales de Secrets Manager y conexión SSL. El modo local usa `psql`, `PGPASSFILE` y un túnel existente.

### Recuperación estructurada (`retrieve_land_use`)

El mismo archivo contiene `retrieve_land_use(activity, zonification)`, limitado a la Tabla 22. Consulta `land_use_compatibility` por documento/tabla, zonificación y coincidencia exacta de nombre o alias. Devuelve valor original, categorías, fuente, páginas y marca pendiente. El helper actual solo usa `psql` local y `PGPASSFILE`; no tiene parámetros de conexión Aurora/Secrets Manager como `retrieve()`.

La consulta no resuelve alias difusos, consultas de toda una zona, tablas estadísticas o Tablas 20/24. Un resultado vacío solo significa que no hubo coincidencia con esos criterios.

### Generación (`answer_question`)

`generar_respuesta.answer_question()` llama a una sola función `retriever_fn(question, top_k)`, normaliza una lista de diccionarios, prepara contexto con referencias `[F1]`, `[F2]`, llama al modelo y valida que las citas emitidas existan entre las fuentes proporcionadas. La forma de fuente actual conserva un conjunto limitado de campos (`documento`, `articulo`, `cita_legal`, `segmento`, fragmento y `pendiente_revision`).

`lambda_function.lambda_handler()` inyecta a `answer_question()` un wrapper de `retrieve()` con conexión Aurora. No llama `retrieve_land_use()`. Por tanto, aunque hay recuperación semántica y un helper SQL de Tabla 22, hoy no existe en el flujo de respuestas una ruta estructurada ni una fusión de resultados entre ambas.

## 3. Arquitectura futura propuesta

```text
Pregunta
  │
  ├─ 1. Analizador/intención (documento, tabla, entidad, zona, periodo)
  │
  ├─ 2a. Recuperación semántica ── legal_embeddings → legal_chunks
  │
  └─ 2b. Recuperación estructurada ── catálogo + tablas SQL tipadas
         (solo cuando la pregunta contiene predicados consultables)
                 │
                 ▼
       3. Normalizador común de evidencia
       - evidencia textual / fila / celda
       - referencia estable
       - texto y datos originales
       - página, tabla, fila, columna, notas
       - needs_review y auditoría
                 │
                 ▼
       4. Integración y deduplicación sin pérdida de origen
                 │
                 ▼
       5. Generador de respuestas con identificadores de fuente
```

El enrutador puede iniciar ambas rutas en paralelo cuando la pregunta requiere una respuesta estructurada y su fundamento narrativo. No debe usar el LLM para inventar un valor que la consulta SQL no encontró. La salida SQL se conserva como evidencia distinta del texto semántico y se combina solo después de comprobar documento, tabla, zona/actividad y página.

## 4. Contrato de evidencia propuesto

Cada evidencia normalizada debe incluir al menos:

```json
{
  "evidence_id": "generado_para_esta_consulta",
  "kind": "semantic_chunk | structured_cell | structured_row",
  "document_id": "ppdu_hipodromo",
  "document_name": "nombre documental",
  "table_id": "tabla_22",
  "table_number_original": 22,
  "table_title_literal": "título verificado",
  "page_pdf": 80,
  "page_printed": null,
  "row_id": "identificador estable",
  "column_id": "identificador estable o zonificación",
  "original_text": "texto o contenido literal de la fuente",
  "original_value": "valor fuente, sin normalización destructiva",
  "normalized_value": null,
  "notes": [],
  "needs_review": true,
  "audit_status": "pendiente",
  "citation_label": "[F1]"
}
```

Es un contrato de diseño, no la forma actual devuelta por `retrieve()` ni por la API. Los campos desconocidos deben permanecer `null`/ausentes como tales, no reconstruirse por suposición. El generador debería citar por `evidence_id`/`citation_label`; la respuesta al usuario debe poder explicar documento, tabla, fila/celda y página, además de mantener `pendiente_revision`.

## 5. Enrutamiento de preguntas

| Pregunta | Ruta primaria | ¿Semántica también? | Motivo / resultado requerido |
|---|---|---|---|
| “¿Qué establece el PPCU sobre determinada actividad?” | Semántica | Sí; SQL si identifica una actividad y zonificación de Tabla 22 | La norma narrativa puede definir condiciones; la celda solo aplica a actividad-zona específica. Si no hay zona, no concluir compatibilidad global |
| “¿Qué valor aparece en una tabla estadística?” | SQL sobre tabla estadística confirmada | Semántica como apoyo para identificar contexto/unidad | Devolver valor literal, unidad, período, fila y página; evitar cálculos no documentados |
| “¿Qué restricciones se aplican a determinada zonificación?” | SQL si se consulta Tabla 22/tabla tipada; semántica para normas narrativas | Sí | Recuperar celdas o parámetros y el texto que explica su alcance, excepciones o términos |
| “¿Qué actividades son compatibles con una zonificación?” | SQL sobre Tabla 22 | Sí, para explicar fuente/notas y limitaciones | Listar estados tal como constan; separar `por validar`, no etiquetarlo como compatible/incompatible |
| “¿Qué disposiciones explican una condición identificada en una tabla?” | Semántica filtrada por documento y, si está disponible, sección/cita | Sí, tras identificar la fila estructurada | SQL localiza condición/celda; búsqueda semántica encuentra disposiciones explicativas; cada salida mantiene su cita |

La búsqueda semántica no es sustituto de un predicado exacto en valores tabulares. SQL no sustituye interpretación textual de excepciones o fundamentos. La ruta debe adaptarse al tipo de tabla verificado: no consultar una tabla que no exista o cuya extracción no esté aprobada.

## 6. Flujos conceptuales

### Pregunta actividad + zona

1. Extraer actividad y zonificación de la pregunta; normalizar solo alias verificados.
2. Consultar SQL con parámetros para la Tabla 22.
3. Si no hay coincidencia exacta, pedir precisión o recuperar semánticamente conceptos cercanos; no convertir la falta de coincidencia en “prohibido”.
4. Recuperar semánticamente la explicación de zonificación/uso si se requiere contexto.
5. Integrar la celda y los fragmentos como evidencias separadas.
6. Indicar el valor literal y la advertencia de revisión. Si es `por validar`, comunicar que el registro no permite concluir permitido/prohibido.

### Pregunta de cifra o estadística

1. Identificar tabla/indicador/territorio/período; si no alcanza para identificar una fila, hacer búsqueda semántica o pedir aclaración.
2. Consultar registro estructurado aprobado.
3. Devolver valor, unidad y denominador como aparecen, más página/tabla/fila.
4. Añadir contexto semántico solo si responde una pregunta explicativa; nunca recalcular silenciosamente.

### Restricción con fundamento

1. SQL recupera condición/valor de la tabla normativa o de protección pertinente.
2. Búsqueda semántica recupera las disposiciones textuales y notas relacionadas.
3. Integrador coteja que se refieran al mismo instrumento, tema y zonificación/elemento.
4. Respuesta cita tanto la fila/celda como el fragmento normativo. Si las fuentes no coinciden o una está pendiente, expresar la limitación en lugar de resolverla por inferencia.

## 7. Integración con generador y API: requisitos futuros

Sin implementar, la futura integración debería:

- Mantener una sola interfaz de orquestación que reciba la pregunta y devuelva una colección de evidencias tipadas, no solo chunks vectoriales.
- Hacer consultas SQL parametrizadas con límites y filtros explícitos de `document_id`, `table_id` y valores; no concatenar entrada de usuario en SQL.
- Tener una ruta de conexión estructurada compatible con el modo Aurora de Lambda y credenciales actuales; el helper local actual no basta.
- Preservar el objeto original que permita reconstruir referencia de tabla, fila, columna, página, notas, estado original y `needs_review`.
- Asignar IDs de cita únicos después de combinar y deduplicar fuentes; no perder la relación de cada cita con la evidencia exacta.
- Evitar que el prompt presente un dato estructurado pendiente como conclusión verificada. `needs_review` debe mantenerse hasta que un proceso humano aprobado cambie el estado.
- Diferenciar ausencia de coincidencia, estado `por validar`, evidencia insuficiente y fallo técnico.
- Definir límites de cantidad/tamaño de filas y chunks y un orden de prioridad reproducible.
- Añadir pruebas offline para cada clase de intención, resultados vacíos, alias, datos pendientes, notas, fuentes duplicadas, y violaciones de integridad de citas antes de considerar un despliegue.

## 8. Riesgos y cuestiones abiertas

1. **Cobertura del inventario:** Tabla 23 no fue localizada en el texto ni en la inspección visual del intervalo 82–89, pero la revisión visual completa del PDF sigue pendiente. No crear un registro de tabla confirmado a partir del hueco numérico.
2. **Procedencia de Tabla 22:** los registros actuales apuntan a página `[80]`, mientras el archivo de fuente dice `PPCU_Hipodromo-80-81.pdf`; requiere cotejo de página/celda. No alterar el JSON.
3. **Notas al pie:** el JSON actual no conserva de forma explícita todas las notas del PDF; una respuesta estructurada no puede ignorarlas cuando sean relevantes.
4. **Generador actual:** sus fuentes actuales se centran en fragmentos y campos bibliográficos limitados; el contrato nuevo requeriría cambios coordinados a normalización, prompt, salida API y pruebas.
5. **Revisión jurídica:** estructura e ingestión no validan vigencia ni aplicabilidad. Una tabla descriptiva no debe presentarse como una regla normativa.
6. **Ambigüedad de consulta:** una actividad, distrito o zonificación puede nombrarse de varias formas; el catálogo de alias debe ser trazable y aprobado, no derivado por coincidencia difusa como hecho jurídico.

## 9. Relación con los otros documentos

La estructura de JSON, el catálogo y el inventario preliminar se definen en [diseno_modelo_datos_PPCU.md](./diseno_modelo_datos_PPCU.md). La comparación de esquemas y los SQL ilustrativos están en [propuesta_esquema_postgresql_PPCU.md](./propuesta_esquema_postgresql_PPCU.md). Los tres documentos son propuestas de diseño; no autorizan implementación.
