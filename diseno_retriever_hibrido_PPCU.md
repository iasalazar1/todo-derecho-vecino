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

El contrato de fuentes de `answer_question()` conserva actualmente documento, artículo/cita, segmento, texto y revisión, pero no una unión tipada para página, fila, columna, actividad, zona o celda. Tampoco distingue en salida fuente literal de interpretación del sistema y conclusión. El prompt exige citas, evidencia suficiente y advertencias, pero no puede suplir esos metadatos ausentes. El procesador PDDU/PPCU usa hoy `articulo` para la numeración decimal de sección (`process_pddu_document()`); el campo no debe reutilizarse así en un contrato futuro.

## 3. Arquitectura futura propuesta

```text
Pregunta
  │
  ├─ 1. Interpretador ligero (reglas, alias verificados, tipo/intención)
  │     └─ criterios con fuente, confianza y estado: explícito/candidato/ambiguo
  │
  ├─ 2a. Recuperación semántica amplia ── legal_embeddings → legal_chunks
  │
  └─ 2b. Recuperación estructurada ── catálogo + tablas SQL tipadas
         (solo tras validar candidatos y con filtros parametrizados)
                 │
                 ▼
       3. Normalizador común de evidencia
       - evidencia semántica / fila / parámetro / celda
       - referencia estable
       - texto y datos originales
       - página física/impresa y localizador tipado, con estado de verificación
       - tabla, fila, columna y celda exacta cuando exista
       - needs_review y auditoría
                 │
                 ▼
       4. Integración con separación de evidencia literal,
          interpretación y conclusión jurídica
                 │
                 ▼
       5. Generador de respuestas con identificadores de fuente
```

Para el MVP, el interpretador recomendado es sencillo: reglas explícitas, catálogos de alias verificados y clasificación de intención. No se propone un sistema de agentes ni varios modelos. La búsqueda semántica debe comenzar amplia. El enrutador puede usar filtros seguros para mejorar la precisión, pero no debe restringir la recuperación con criterios dudosos. Las rutas semántica y SQL pueden ejecutarse en paralelo una vez que la pregunta contenga predicados consultables y la evidencia estructurada esté confirmada.

### Interpretación y niveles de confianza de criterios

El interpretador identifica candidatos para actividad/giro, zonificación, colonia/ámbito territorial, documento, tipo de consulta e intención. Debe registrar el texto detectado, catálogo/regla aplicada, nivel de confianza y filtros finalmente usados.

| Nivel | Ejemplo conceptual | Uso permitido |
|---|---|---|
| A. Explícito | La pregunta nombra literalmente una clave HCS o un giro claro del catálogo | Se puede usar como criterio SQL o de búsqueda si valida contra el catálogo y tabla pertinentes |
| B. Inferido con alta confianza | Alias o expresión reconocida por una regla/catalogo verificado | Candidato, no filtro excluyente todavía; validar contra catálogo, metadatos o evidencia recuperada antes de restringir |
| C. Ambiguo/insuficiente | Actividad genérica, zonificación dudosa, territorio omitido o varias coincidencias | No aplicar filtro que excluya evidencia; mantener búsqueda semántica amplia o solicitar aclaración si cambia materialmente la respuesta |

Los umbrales de confianza deben fijarse con pruebas futuras, no se presuponen aquí. Una inferencia errónea nunca debe suprimir evidencia potencialmente relevante sin dejar rastro. Si no puede determinarse actividad o zonificación con certeza suficiente, la respuesta debe decirlo o pedir aclaración, no adivinar.

Por ejemplo, la mención de “restaurante” por sí sola puede identificar un giro candidato, pero no determina la zonificación ni el ámbito territorial. No debe convertirse en un filtro de zona; se mantiene una búsqueda semántica amplia o se solicita la zonificación cuando sea necesaria para una consulta exacta.

### Salvaguardas para filtros estructurados

- Parametrizar cada valor SQL; usar consultas preparadas y listas permitidas para identificadores/tipos.
- No concatenar texto libre, alias o nombres de usuario en la sentencia SQL.
- Resolver `document_key` y `table_key` contra catálogos aprobados; usar `document_id` y `table_pk` solo como IDs numéricos internos. En el DDL heredado de Tabla 22, `documento_id`/`tabla_id` son claves textuales, no IDs internos.
- Aplicar filtros duros solo para criterios explícitos o ya validados. Candidatos inferidos no validados se usan para expansión/búsqueda paralela, no para exclusión.
- Registrar criterios detectados, su origen/confianza, predicados aplicados y razón de exclusión.
- Si filtro validado no devuelve filas, distinguir “sin coincidencia exacta” de “prohibido”; ampliar búsqueda o pedir precisión.

## 4. Contrato de evidencia propuesto

Cada evidencia normalizada debe incluir al menos:

```json
{
  "evidence_id": "generado_para_esta_consulta",
  "tipo_evidencia": "semantic_chunk | structured_row | structured_cell",
  "clase_dato": "texto_normativo | matriz_cualitativa | parametro_normativo_cuantitativo | dato_estadistico_diagnostico",
  "document_id": null,
  "document_key": "clave_textual_estable",
  "document_name": "nombre documental",
  "table_pk": null,
  "table_key": "tabla_22",
  "table_number_original": 22,
  "table_title_literal": "título verificado",
  "page_pdf_start": null,
  "page_pdf_end": null,
  "page_printed": null,
  "localization_status": "pending",
  "tipo_localizador": "planeacion_urbana | legislativo | tabla",
  "localizador": {},
  "row_key": null,
  "column_key": null,
  "cell_key": null,
  "activity_original": null,
  "zonification_original": null,
  "cell_original": null,
  "valor_original": null,
  "unidad_original": null,
  "periodo_original": null,
  "ambito_original": null,
  "texto_original": null,
  "reference_original": null,
  "notes": [],
  "needs_review": true,
  "estado_revision_juridica": "pendiente",
  "source_reference": null,
  "interpretacion_sistema": null,
  "conclusion_juridica": null,
  "citation_label": "[F1]"
}
```

Es un contrato conceptual común, no la forma actual devuelta por `retrieve()` ni por la API. Campos no aplicables pueden omitirse; datos desconocidos deben permanecer ausentes/null, no reconstruirse. `document_id` y `table_pk` son IDs numéricos internos cuando se obtienen de la base; `document_key` y `table_key` son claves externas textuales estables. El objeto de evidencia conserva la clave externa aunque incluya el ID interno. `localization_status` usa `pending`, `verified` o `unavailable`; describe cotejo documental, no revisión jurídica. `page_pdf_start`/`page_pdf_end` son páginas físicas del PDF; `page_printed` solo se informa si se verificó directamente en la fuente. La forma equivalente del contrato JSON en español es `pagina_pdf_inicio`/`pagina_pdf_fin`, `pagina_impresa` y `estado_verificacion_localizacion`. `tipo_localizador` determina semánticamente `localizador`:

- `legislativo`: título/capítulo/sección/artículo/fracción/inciso.
- `planeacion_urbana`: capítulo/apartado/sección/subsección/numeración jerárquica; no utilizar `articulo`.
- `tabla`: número/ID, página, fila, columna, actividad, zonificación, celda y valor.

En `localizador` tabular se conserva `table_key`, número original, fila, columna, actividad, zonificación, celda y valor según aplique. Una fila/celda exacta se identifica solo si fue verificada; el resultado de una consulta a nivel de tabla no se presenta como cita exacta de celda. La página física del PDF, la página impresa y el estado de verificación se preservan por separado. El procesador actual no guarda página exacta por chunk, por lo que habrá que mejorar o validar el mapeo desde PDF a texto/chunk antes de afirmar una página. `contexto_superior` y `cita_legal` no resuelven por sí solos esa localización.

Separación semántica obligatoria:

1. **Evidencia recuperada:** texto/celda literal atribuible a fuente, con procedencia y estado de revisión.
2. **Interpretación del sistema:** intención, alias, normalización o explicación, etiquetada como interpretación y con trazabilidad.
3. **Conclusión jurídica:** solo puede derivarse de evidencia suficiente, aplicabilidad verificada y revisión adecuada; no es el contenido de una celda ni un resultado automático del SQL.

## 5. Enrutamiento de preguntas

| Pregunta | Ruta primaria | ¿Semántica también? | Motivo / resultado requerido |
|---|---|---|---|
| “¿Qué establece el PPCU sobre determinada actividad?” | Clasificar intención; búsqueda semántica amplia | SQL si se identifica actividad + zonificación verificadas en Tabla 22 | La regla narrativa puede contener condición; no concluir compatibilidad desde la celda si no se conoce zona |
| “¿Qué valor aparece en una tabla estadística?” | SQL si tabla/indicador/ámbito se identifican o validan | Semántica amplia para localizar tabla/unidad si no hay filtros seguros | Devolver valor literal, unidad, periodo, ámbito, página y fila; no calcular |
| “¿Qué restricciones se aplican a determinada zonificación?” | SQL para tabla/parametría confirmada; filtros solo con zona verificada | Sí para disposiciones y excepciones | Recuperar estado/valor literal y evidencia narrativa; no mezclar matriz cualitativa con parámetro cuantitativo |
| “¿Qué actividades son compatibles con una zonificación?” | SQL sobre Tabla 22 con zona explícita/validada | Sí para contexto y notas | Presentar cada estado original, separar `por validar`; no asignar significado jurídico adicional |
| “¿Qué disposiciones explican una condición identificada en una tabla?” | SQL identifica primero fila/celda/condición | Sí, recupera texto de apoyo en búsqueda amplia con filtros solo validados | Citar la fila y la disposición separadamente; no presentar interpretación como norma literal |

La búsqueda semántica no es sustituto de un predicado exacto en valores tabulares. SQL no sustituye interpretación textual de excepciones o fundamentos. La ruta debe adaptarse al tipo de tabla verificado: no consultar una tabla que no exista o cuya extracción no esté aprobada.

### Distinción de clases durante el enrutamiento

- **Matriz cualitativa:** igualdad de actividad/zona contra catálogos y recuperación literal de estado. Sin score o cálculo que convierta `por validar`.
- **Parámetro normativo cuantitativo:** consulta de valor, unidad, zonificación/ámbito y disposición de origen. No derivar el porcentaje, capacidad, superficie o cantidad.
- **Estadística/diagnóstico:** consultar cifra, periodo, ámbito y fuente. No calcular tasas, promedios, totales o indicadores derivados sin metodología explícita y autorización.

`clase_dato` y `tipo_evidencia` identifican la ruta y el formato de respuesta; no declaran validez ni fuerza jurídica.

## 6. Flujos conceptuales

### Fusión, deduplicación y discrepancias

La integración no debe colapsar evidencias distintas solo porque hablan del mismo tema. Debe conservar cada evidencia y su procedencia, y eliminar únicamente duplicados que representen el mismo fragmento o la misma fila/celda de la misma versión de fuente. Como clave de comparación se propone usar `document_key`, hash/versión de origen, tipo de localizador y ubicación; para datos tabulares se añade `table_key` y fila/celda, y para chunks semánticos su identificador de chunk/segmento. Si el mismo pasaje aparece en más de un resultado, conservar una evidencia canónica y registrar sus referencias equivalentes.

Prioridad de presentación:

1. Para el valor literal de una actividad-zonificación, la celda estructurada exacta y localizada es la evidencia primaria; devolver literalmente su estado y `needs_review`.
2. Los fragmentos semánticos se mantienen como evidencia separada para contexto, notas, condiciones o fundamento narrativo; no se fusionan dentro del valor de celda.
3. Si una celda no está localizada/verificada o la consulta solo identifica la tabla, no elevarla a evidencia exacta. La búsqueda semántica puede aportar contexto, pero no sustituye ese dato.
4. Asignar etiquetas de cita únicas después de deduplicar, manteniendo una relación estable entre cada etiqueta, evidencia y fuente.

Si la evidencia estructurada y la semántica parecen contradecirse, conservar ambas con sus localizadores y estado de revisión, señalar que hay una discrepancia y no resolverla automáticamente por puntuación, fecha supuesta o inferencia. Si la contradicción impide una respuesta fiable, declarar insuficiencia y solicitar revisión/precisión. Ausencia de coincidencia SQL no significa prohibición ni prueba de inexistencia.

### Pregunta libre antes de filtrar

1. Recibir la pregunta y clasificar su intención (compatibilidad, parámetro, estadística/diagnóstico, explicación normativa u otra) mediante reglas sencillas.
2. Extraer candidatos a actividad, zonificación, territorio y documento. Registrar texto fuente, regla/catálogo y confianza.
3. Aplicar los tres niveles: criterios explícitos se validan en catálogo antes del SQL; inferencias de alta confianza siguen siendo candidatos hasta validación; ambiguos no generan filtros excluyentes y mantienen búsqueda semántica más amplia o pregunta aclaratoria.
4. Ejecutar SQL parametrizado solo para tabla identificada y predicados validados. En paralelo, hacer recuperación semántica amplia o restringida solo por criterios confirmados.
5. Integrar evidencias en el contrato común, sin descartar procedencias ni estados.
6. Si no hay certeza suficiente, informar que el sistema no determinó actividad/zona o pedir aclaración. Un valor desconocido no se sustituye por una conclusión.

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
- Hacer consultas SQL parametrizadas con límites y filtros explícitos; resolver `document_key`/`table_key` a `document_id`/`table_pk` en la base y no concatenar entrada de usuario en SQL. Los nombres heredados `documento_id`/`tabla_id` solo aplican al DDL actual de compatibilidad.
- Implementar interpretación ligera por reglas, catálogo de alias verificados y clasificación de intención; registrar criterios detectados, confianza, validación y filtros aplicados. No añadir sistema de agentes o varios modelos para el MVP.
- Mantener búsqueda semántica amplia cuando los criterios sean ambiguos y usar candidatos inferidos solo tras validación antes de filtrar.
- Tener una ruta de conexión estructurada compatible con el modo Aurora de Lambda y credenciales actuales; el helper local actual no basta.
- Preservar el objeto original que permita reconstruir referencia de tabla, fila, columna, página, notas, estado original y `needs_review`.
- Preservar página física del PDF y página impresa en campos separados, con un estado de verificación de localización distinto de `needs_review` y de la revisión jurídica.
- Extender el procesador y el contrato de fuente para localizadores legislativos, de planeación urbana y tabulares; no usar `articulo` para secciones decimales y resolver la falta de páginas exactas.
- Extender normalización, prompt y serialización de respuesta para mantener evidencia literal, interpretación y conclusión separadas; preservar `document_key` y page/table/row/cell en citas.
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

## Cambios de esta revisión

- Se añadió interpretación ligera de pregunta libre con criterios explícitos, inferidos de alta confianza y ambiguos, además de registro de criterios/filtros y salvaguardas contra exclusión accidental.
- Se armonizó el contrato común de evidencia con `document_id` numérico y `document_key` externo, clases de dato y localizadores tipados legislativo/planeación/tabla.
- Se homologaron `table_pk` numérico y `table_key` textual, así como página física, página impresa y estado de verificación del localizador.
- Se definieron reglas de fusión: deduplicar solo evidencia de la misma fuente/ubicación, priorizar la celda exacta para su valor literal, conservar por separado el contexto semántico y no resolver discrepancias automáticamente.
- Se documentaron las limitaciones existentes: secciones decimales guardadas hoy en `articulo`, falta de página exacta por chunk, helper estructurado local no conectado a `answer_question()`/Lambda y diferencias de contrato/cita.
- Se reforzó la separación entre evidencia recuperada, interpretación del sistema y conclusión jurídica, además de no hacer cálculos o reinterpretar estados.
- Permanecen pendientes el cotejo visual completo, la revisión de Tabla 22, la comprobación de la base viva, la aprobación del contrato y cualquier cambio de código, SQL o infraestructura.
