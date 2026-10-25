# Registro de evaluación semántica — Todo Derecho Vecino

## Propósito

Este registro documenta la calidad de la recuperación semántica del MVP. El archivo estructurado `tests/evaluacion_semantica.json` es la fuente de verdad para consultas, ejecuciones, resultados, anotaciones y métricas. Este Markdown define el protocolo y resume las decisiones para que las evaluaciones sean reproducibles.

## Estado inicial

- Consulta registrada: `SEM-001`, sobre obligaciones de establecimientos mercantiles frente al ruido.
- Ejecución de línea base observada: `SEM-001-RUN-2026-10-25-BASELINE-01`.
- Recuperación: 5 resultados; los cinco pertenecen a la Ley de Establecimientos Mercantiles.
- Anotaciones humanas: pendientes. No se ha fijado una Precision@5 definitiva.
- Corpus de la base: 5 documentos, 1,235 chunks y 1,369 embeddings de 1,024 dimensiones, según la verificación de carga.
- Revisión de vigencia y correspondencia jurídica: pendiente.

Los resultados y fragmentos de la línea base se transcribieron de la salida de evaluación compartida el 25 de octubre de 2026. La versión exacta del commit ejecutado no se registró en esa corrida; no atribuirle retrospectivamente un SHA.

## Etiquetas de relevancia

| Etiqueta | Significado | Tratamiento |
|---|---|---|
| `2` | Relevante | Cuenta como relevante para Precision@k binaria. |
| `1` | Parcialmente relevante | Se conserva; no cuenta como relevante en la métrica binaria principal. Puede usarse en análisis graduados si se define una regla explícita. |
| `0` | Irrelevante | No cuenta como relevante. |
| `R` | Requiere revisión | No calcular métrica definitiva mientras existan resultados R sin resolver. |
| `null` | Sin anotar | Anotación pendiente; no equivale a irrelevante. |

Las etiquetas son una valoración de pertinencia respecto de la pregunta, no una certificación de vigencia ni una opinión jurídica definitiva.

## Métricas

### Precision@k

`Precision@k = número de resultados con etiqueta 2 entre los primeros k / k`.

Para `Precision@5`, el denominador es 5 incluso si el sistema devuelve menos de cinco resultados; se debe registrar el número real de resultados para interpretar el caso. No calcular el resultado definitivo mientras alguna etiqueta del top-k esté pendiente o marcada R.

### NDCG@k

Mide la calidad del ordenamiento y permite conservar los grados de relevancia (2, 1, 0). Debe implementarse con una fórmula documentada y la misma política de etiquetas en todas las versiones.

### Recall@k

Sólo calcular cuando exista un conjunto de fragmentos relevantes conocidos y revisados para la consulta. La ausencia de una anotación exhaustiva no permite afirmar que se conoce el total de resultados relevantes.

### Cobertura de fuentes

Comparar las fuentes recuperadas en top-k con las fuentes esperadas para la pregunta. Las fuentes esperadas deben definirse y validarse jurídicamente antes de comparar versiones. No exigir que todas las leyes aparezcan en todas las consultas: sólo las que sean pertinentes para la pregunta.

## Protocolo para cada nueva ejecución

1. No sobrescribir ejecuciones anteriores en `evaluacion_semantica.json`; agregar un objeto nuevo a `queries[].runs[]`.
2. Asignar un `run_id` único y registrar fecha, comando, rama/commit, versión del corpus, `top_k` y resultados completos disponibles.
3. Conservar por resultado la posición, fuente, artículo, cita, distancia, identificador de fragmento si está disponible, texto recuperado, estado `needs_review` y etiqueta humana.
4. Anotar cada resultado por pertinencia. Si hay dudas sobre interpretación normativa, usar `R` y registrar la razón.
5. Calcular métricas sólo con reglas documentadas. Mantener en null las métricas que no puedan calcularse de forma válida.
6. Comparar con la línea base utilizando las mismas consultas, el mismo corpus o una versión de corpus identificada y el mismo protocolo de anotación.
7. No modificar el algoritmo del retriever hasta que exista un diagnóstico reproducible que identifique la causa del comportamiento observado.

## Hallazgo importante: smoke test por documento

`tests/smoke_test_similarity.py` es útil como prueba de humo de similitud: genera un embedding de una pregunta y ejecuta una búsqueda vectorial separada por cada nombre de documento de una lista fija. La lista actual contiene sólo:

- Programa Parcial de Desarrollo Urbano Hipódromo.
- Ley de Establecimientos Mercantiles para la Ciudad de México.

El SQL del smoke test filtra explícitamente con `WHERE d.name = :'documento'`. Por eso **ese script no prueba la recuperación de las cinco leyes** y no puede usarse como evidencia de que la Ley de Cultura Cívica esté siendo recuperada o excluida en la búsqueda general.

En cambio, el SQL de `retrieve()` en `retriever.py` no incluye un filtro por nombre de documento: busca candidatos en `legal_embeddings` y luego reordena ese conjunto. La salida de SEM-001 con cinco resultados de una misma ley puede deberse al ranking; por sí sola no demuestra que las demás fuentes estén excluidas.

## Diagnóstico siguiente: ruido y Ley de Cultura Cívica

Antes de cambiar `retrieve()`:

1. Confirmar los nombres de las cinco fuentes en `legal_documents` y que tienen embeddings.
2. Ejecutar una consulta diagnóstica que muestre los mejores candidatos vectoriales por fuente, sin modificar el retriever de producción.
3. Comprobar si aparecen fragmentos de la Ley de Cultura Cívica relacionados con ruido, molestias a terceros o consecuencias cívicas.
4. Revisar jurídicamente los fragmentos y definir si esa ley es una fuente esperada para SEM-001.
5. Comparar esos candidatos con el ranking híbrido actual.

Una coincidencia literal de la palabra “ruido” no basta por sí sola para etiquetar un fragmento como relevante: la disposición debe contribuir a responder la pregunta.

## Limitaciones actuales

- Las anotaciones de SEM-001 siguen pendientes; los valores `relevance` están en `null`.
- La fuente esperada Ley de Cultura Cívica está marcada como provisional hasta identificar y revisar la disposición aplicable.
- Las métricas están en `null` hasta completar anotación y validación.
- La línea base no tiene registrado el SHA exacto del commit que la produjo.
- Este registro no modifica la base de datos ni cambia el algoritmo de recuperación.

## Ubicación de los artefactos

- `tests/evaluacion_semantica.json`: registro incremental estructurado.
- `tests/evaluacion_semantica.md`: protocolo, hallazgos y guía de interpretación.
- `tests/evaluacion_semana5.json`: casos existentes de evaluación estructurada y semántica.
- `tests/smoke_test_similarity.py`: smoke test vectorial por documento.
