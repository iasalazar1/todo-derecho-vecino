# ajustes_pendientes.md
# Proyecto: Todo Derecho Vecino — MVP de estancia
# Última actualización: 11 de noviembre de 2026 — auditoría de fuentes PPCU/PDDU y pendientes S9–S10
# Mantenedor: Agente de IA (bajo validación del usuario)

## 0. Propósito y reglas de uso de este archivo

Este archivo es la **memoria a largo plazo** del proyecto. Todo aquello que
deba recordarse entre sesiones debe quedar registrado aquí:

- Pendientes técnicos, bugs y bloqueos.
- Decisiones que no deben revertirse.
- Ideas o mejoras que quedan fuera del MVP actual.
- Datos que faltaron y que se consultaron al usuario (con la respuesta).
- Observaciones de operación (costos, credenciales, artefactos).

### Reglas
1. **Registrar inmediatamente:** en cuanto surja un pendiente, una decisión
   o un dato faltante, se documenta aquí antes de continuar.
2. **No borrar pendientes cerrados:** se mueven a la sección de historial
   con fecha de cierre y evidencia.
3. **Cada pendiente tiene ID, origen, prioridad, semana objetivo y estado.**
4. **Si un pendiente bloquea la semana en curso, se marca como BLOQUEANTE.**
5. **El agente debe consultar este archivo al inicio de cada sesión.**

---

## 1. Pendientes BLOQUEANTES para la Semana 8 (frontend)

| ID | Descripción | Origen | Estado | Notas |
|---|---|---|---|---|
| B8-01 | Verificar que `scripts/probar_retriever.py` exista en el árbol de trabajo real del repo. | Bitácora 18-oct | ⬜ Abierto — trasladado a S9 | Confirmar junto con los scripts de evaluación antes de ejecutarlos o versionarlos. |
| B8-02 | Confirmar estado operativo de AWS: ¿DEV está apagado o encendido? Verificar con `./terraform/dev-status.sh`. | Bitácora S7 y control de costos | ⬜ Abierto — trasladado a S9 | No se infiere el estado de DEV a partir del despliegue del frontend. Verificar antes de pruebas o apagado. |
| B8-03 | Confirmar que el endpoint `POST https://1zhgtujka8.execute-api.us-east-1.amazonaws.com/consulta` responde correctamente desde el frontend público. | Bitácora S7–S8 | ✅ Cerrado — 9-nov-2026 | El usuario confirmó una respuesta correcta desde CloudFront, similar a la prueba local. |
| B8-04 | Definir estructura del frontend. | Arquitectura MVP + alcance S8 | ✅ Cerrado — 9-nov-2026 | Se implementó frontend estático con HTML/CSS/JavaScript, sin framework. |
| B8-05 | Definir y verificar la presentación de citas `[F1]`–`[F5]` con respuestas JSON reales. | Alcance S8 | 🟡 Parcial — revisar en S9 | El frontend ya recibe y presenta respuesta y fuentes; falta revisar casos variados y la interpretación jurídica de cada estado. |
| B8-06 | Confirmar cómo se presenta al usuario final el indicador `pendiente_revision: true` de cada fuente. | Bitácora S5, S7 | ⬜ Pendiente de verificación en S9 | No asumir que el indicador se muestra correctamente sin revisar el frontend y una respuesta JSON real. |
| B8-07 | Decidir si se agrega autenticación o se mantiene la API abierta durante el MVP. | Bitácora S7 + acuerdo del usuario 10-nov-2026 | ✅ Decidido — autenticación programada para S10 | No se implementará como parte de S9. Incorporar autenticación de la API en Semana 10; hasta entonces, la API abierta sigue siendo una limitación del MVP y no es apta para producción. |

---

## 2. Pendientes técnicos para Semanas 8–10

### 2.1 Semana 8 (frontend)

| ID | Descripción | Estado | Notas |
|---|---|---|---|
| S8-01 | Construir interfaz de chat responsiva. | ✅ Completado — 9-nov-2026 | Frontend estático HTML/CSS/JS publicado en CloudFront. |
| S8-02 | Conectar frontend al endpoint `/consulta`. | ✅ Completado — 9-nov-2026 | Prueba pública desde CloudFront confirmada por el usuario. |
| S8-03 | Renderizar respuesta + citas `[F1]`–`[F5]`. | ✅ Completado técnicamente — 9-nov-2026 | La UI presenta respuesta y fuentes; revisión de escenarios y estados jurídicos pasa a S9. |
| S8-04 | Manejar errores HTTP (400, 404, 5xx) en la UI. | 🟡 Verificación pendiente | Confirmar con pruebas específicas durante E2E de S9. |
| S8-05 | Añadir indicador de carga mientras se espera respuesta. | 🟡 Verificación pendiente | Confirmar mediante inspección del frontend y prueba de latencia en S9. |
| S8-06 | Documentar el despliegue del frontend en `Instructivo_operacion.md`. | ✅ Completado — 9-nov-2026 | Nueva sección 26: S3, CloudFront, CORS, verificación y distinción BASE/DEV. |
| S8-07 | Revisar la interpretación y presentación de respuestas de la API con distintos JSON reales, sin modificar inicialmente el contrato del backend. | ⬜ Trasladado a S9 | Revisar evidencia suficiente, citas pendientes, evidencia insuficiente y error técnico. No cambiar backend/corpus ni marcas de revisión sin autorización. |

#### Criterios pendientes para presentación jurídica de respuestas (S8-07)

**Secuencia acordada:** terminar primero el flujo técnico del frontend con el contrato actual de la API. No modificar el backend ni su estructura de respuesta durante esta etapa, salvo que las pruebas técnicas demuestren una incompatibilidad concreta. Una vez conectado el flujo, revisar respuestas JSON reales y ajustar la interpretación visual.

La interfaz deberá distinguir, sin confundirlos, estos escenarios:

1. **Respuesta con evidencia:** presentar la respuesta y sus referencias recuperadas.
2. **Referencias pendientes de revisión:** conservar y hacer visible `pendiente_revision`; advertir que una cita recuperada no equivale a una disposición jurídicamente validada.
3. **Evidencia insuficiente:** comunicar claramente que el sistema no cuenta con fundamentos suficientes y evitar presentar una conclusión como confirmada.
4. **Error técnico:** diferenciar errores HTTP o de conexión de una respuesta válida del agente, e indicar que se puede reintentar.

**Criterios de calidad jurídica que deben reflejarse en la UI:**
- Distinguir recuperación de fragmentos, fundamentación de la respuesta y validación jurídica de vigencia y aplicabilidad.
- No presentar la vigencia normativa como confirmada si no ha sido verificada.
- Permitir consultar el fragmento y los datos de cada cita sin saturar la respuesta principal.
- Mantener visible que el sistema ofrece orientación y no un dictamen ni una resolución oficial.

**Antecedente que motiva el pendiente:** en las pruebas previas del backend se obtuvo una respuesta HTTP 200 con cinco citas, pero todas tenían `pendiente_revision=true`; además, no se recuperaron los instrumentos urbanos necesarios para resolver una consulta de compatibilidad de giro. Por tanto, la existencia de citas no debe interpretarse automáticamente como evidencia suficiente.

**Alcance:** es un ajuste de presentación e interpretación del frontend posterior a completar la conexión técnica. No autoriza por sí mismo cambios al contrato de la API, al backend, al corpus ni a las marcas de revisión.

---

### 2.2 Semana 9 (integración, pruebas, hardening)

| ID | Descripción | Estado | Notas |
|---|---|---|---|
| S9-01 | Pruebas E2E del flujo completo (usuario → frontend → API → Lambda → Aurora → Bedrock → respuesta). | ⬜ Pendiente | — |
| S9-02 | Revisión de permisos IAM de mínimo privilegio (Lambda, Terraform, usuario admin). | ⬜ Pendiente | Ver bitácora S2 y S7. |
| S9-03 | Activar y verificar logs operativos básicos en CloudWatch para Lambda/API Gateway. | ⬜ Pendiente | Registrar eventos técnicos, errores, códigos de estado y latencias. No registrar el texto completo de consultas ni respuestas por defecto; primero verificar qué registra actualmente el código. |
| S9-04 | Verificar la configuración de throttling de API Gateway y adoptar 5 req/s con burst 10 como parámetro inicial para las pruebas del MVP. | 🟡 Acordado; falta verificar configuración real | El valor 5/10 se acepta para esta etapa de pruebas. No se considera un dimensionamiento definitivo de producción: después del MVP se observarán rechazos 429, volumen, latencia y errores mediante CloudWatch y se ajustará con pruebas de carga y uso real. |
| S9-05 | Mantener documentada la ausencia de autenticación durante las pruebas de S9 y preparar el trabajo de autenticación para S10. | ✅ Decidido — 10-nov-2026 | La autenticación no se adelanta a S9; queda programada como pendiente S10. Ver S10-08. |
| S9-06 | Documentar hallazgos de pruebas en `Bitacora.md` y `Reporte_Semanal_09.md`. | ⬜ Pendiente | — |
| S9-07 | Determinar y documentar qué datos de cada consulta quedan registrados actualmente en CloudWatch/Lambda/API Gateway; verificarlo en código y logs reales, sin asumir que existe un historial consultable de preguntas. | ⬜ Pendiente | Distinguir logs operativos de un dataset de evaluación. No afirmar que las consultas se almacenan para medir calidad hasta comprobarlo. |
| S9-08 | Definir un conjunto fijo y versionado de consultas de evaluación, separado de las consultas espontáneas de usuarios. | ⬜ Pendiente | Incluir preguntas representativas de los cinco instrumentos y casos de evidencia insuficiente; conservar pregunta, respuesta esperada, fuentes/disposiciones relevantes y criterio de corrección. |
| S9-09 | Medir calidad del recuperador sobre el conjunto fijo con `Precision@k` y `Recall@k` (y, si los datos esperados permiten ordenar relevancia, `MRR` o `nDCG@k`). | ⬜ Pendiente | Fijar k y la unidad evaluada (fragmento, disposición o documento) antes de correr la evaluación. El `Precision@5 = 0.40` de una pregunta sigue siendo solo un dato preliminar, no una línea base global. |
| S9-10 | Evaluar manualmente la calidad de respuestas generadas y sus citas con una rúbrica reproducible. | ⬜ Pendiente | Puntuar por separado: fidelidad a las fuentes recuperadas, exactitud/localización de citas, cobertura de aspectos solicitados, reconocimiento de evidencia insuficiente y ausencia de afirmaciones no sustentadas. Revisión humana; no confundir con métricas del retriever. |
| S9-11 | Definir una política mínima de telemetría y privacidad antes de registrar consultas reales para análisis. | ⬜ Pendiente | Determinar campos, retención, acceso y anonimización; evitar registrar datos personales o contenido sensible innecesario. No crear una tabla nueva ni persistir preguntas completas sin validar necesidad, consentimiento/aviso y diseño. |
| S9-12 | Verificar en CloudWatch los logs operativos de una consulta exitosa y de una fallida, y documentar qué puede observarse sobre throttling y errores. | ⬜ Pendiente | Separar métricas operativas (incluidos 429, 4xx/5xx y latencia) del conjunto versionado de evaluación de calidad. No asumir que CloudWatch conserva un historial completo de preguntas. |

#### Consideraciones para medir calidad en Semana 9

La prueba satisfactoria desde CloudFront del 9 de noviembre de 2026 acredita que el flujo público funciona técnicamente en el caso probado. **No acredita por sí sola la calidad global del RAG ni constituye una medición de score.** Las consultas hechas manualmente desde el navegador tampoco deben considerarse automáticamente un conjunto de evaluación.

Separar tres niveles de medición:

1. **Operación E2E:** registrar resultado HTTP, errores por etapa y latencia total (y, si está disponible, latencia de recuperación y generación). Reportar número de pruebas, éxitos/fallos y tasa de error. Esto mide disponibilidad y comportamiento técnico, no corrección jurídica.
2. **Recuperación:** ejecutar un conjunto fijo de preguntas con fragmentos/disposiciones relevantes etiquetados previamente. Calcular `Precision@k` y `Recall@k`; usar `MRR` o `nDCG@k` solo si se definió una escala de relevancia y el orden esperado. Reportar resultados por pregunta y agregados, además de fallos por instrumento. No mezclar la búsqueda semántica con la consulta estructurada de Tabla 22 en una sola métrica.
3. **Generación y citas:** aplicar una rúbrica de revisión humana a respuestas completas. Evaluar por separado fidelidad al contexto recuperado, correspondencia de cada cita con la fuente, cobertura, manejo de incertidumbre/evidencia insuficiente y afirmaciones no sustentadas. La vigencia y aplicabilidad normativa requieren revisión jurídica independiente.

**Estado de almacenamiento de consultas:** todavía no está verificado si el código de Lambda registra el texto de las preguntas, los resultados recuperados o las respuestas, ni si API Gateway conserva datos suficientes para reconstruir una consulta. CloudWatch Logs se contempla en S9-03 como registro básico de operación; eso no equivale a una base histórica etiquetada ni a un mecanismo de scoring. En S9-07 se inspeccionarán el código y los logs existentes antes de decidir si hace falta instrumentación adicional.

**Regla para datos reales:** no usar consultas espontáneas de usuarios como benchmark sin etiquetarlas y revisar su representatividad. Si se decide conservarlas, minimizar datos, evitar información personal/sensible, definir acceso y retención y documentar el aviso correspondiente. No almacenar el contenido completo de consultas por defecto ni crear tablas nuevas sin decisión y autorización.

**Resultado esperado de S9:** un informe que separe métricas operativas, métricas del retriever y evaluación humana de respuestas; indique tamaño y composición del conjunto, criterios, k, resultados por caso, limitaciones y pendientes jurídicos. El conjunto inicial se limitará al corpus MVP de cinco instrumentos, pero su diseño deberá ser extensible para incorporar posteriormente el corpus legal completo (más de 20 instrumentos), sin cambiar la definición de evaluación en cada ampliación. Mantener `needs_review = true` / `pendiente_revision = true`.

### 2.3 Semana 10 (cierre y entrega)

| ID | Descripción | Estado | Notas |
|---|---|---|---|
| S10-01 | Corregir hallazgos de S9. | ⬜ Pendiente | — |
| S10-02 | Documentar arquitectura final (diagrama + descripción). | ⬜ Pendiente | Puede basarse en la imagen de arquitectura. |
| S10-03 | Preparar demo funcional. | ⬜ Pendiente | — |
| S10-04 | Verificar que los 10 reportes semanales estén en Drive. | ⬜ Pendiente | Link: https://drive.google.com/drive/folders/1-f1tkBKLP7c8aZo-IU9_Zb3ME4CEIB9K |
| S10-05 | Verificar consistencia entre `Bitacora.md`, `Instructivo_operacion.md` y `ajustes_pendientes.md`. | ⬜ Pendiente | — |
| S10-06 | Confirmar que `terraform/base` y `terraform/dev` reconstruyen el sistema desde cero. | ⬜ Pendiente | — |
| S10-07 | Apagar DEV y conservar artefactos (embeddings JSONL, chunks, SQL). | ⬜ Pendiente | — |
| S10-08 | Implementar autenticación para la API y documentar su configuración y operación. | ⬜ Pendiente — acordado 10-nov-2026 | La API sin autenticación se tolera únicamente como limitación temporal del MVP de pruebas. Definir el mecanismo, autorización, gestión de credenciales/tokens y pruebas antes de considerar el sistema apto para usuarios externos o producción. |

---

## 3. Pendientes de calidad jurídica y de datos

| ID | Descripción | Origen | Prioridad | Semana objetivo | Estado |
|---|---|---|---|---|---|
| J-01 | Completar las URLs reales de la Gaceta Oficial en `documentos_config.json` (20 documentos con `"fuente": "PENDIENTE: URL..."`). Buscar en `data.consejeria.cdmx.gob.mx`. | Bitácora fase 1 | Media | Post-MVP o S9 | ⬜ Abierto |
| J-02 | Limpiar manualmente bloques de índice duplicados en PPCU Hipódromo (numeración 1.1 a 8.4 repetida en 3 pasadas). | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-03 | Verificar que la corrección del título de PDDU-Cuauhtémoc quede aplicada en el procesador y en todos los artefactos derivados. El JSON de `mvp-estancia` ya identifica el documento como “Programa Delegacional de Desarrollo Urbano de Cuauhtémoc”; la copia de `main` conserva el título incorrecto de Hipódromo. | Bitácora S3 + comparación de ramas 11-nov-2026 | Alta | S9 | 🟡 Parcial — corregido en JSON de `mvp-estancia`; falta verificar el procesador y la regeneración |
| J-04 | Confirmar que las versiones de dos documentos son correctas: Ley Orgánica de Alcaldías (v6.1 config vs v6.4 archivo) y Reglamento LEM (v2 config vs v1 archivo). | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-05 | Validar `autoridad_ner.py` (spaCy + `es_core_news_sm`) en entorno local; confirmar que `sujetos_obligados` se llena correctamente. | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-06 | Afinar heurística de `tipo_disposicion`: casi el 100% de fragmentos quedan `needs_review: true`. | Bitácora fase 1 | Baja | Post-MVP | ⬜ Abierto |
| J-07 | Auditar la extracción y los chunks de PPCU Hipódromo y PDDU Cuauhtémoc contra los PDF originales, comenzando por índice, jerarquía, continuidad, tablas/cuadros, páginas y procedencia. No regenerar embeddings antes de aprobar la corrección de fuentes y JSON. | Bitácora fase 1 + auditoría estática 11-nov-2026 | Bloqueante para regenerar corpus | S9 | ⬜ Abierto — auditoría inicial de JSON completada; falta cotejo visual con PDF |
| J-08 | Validar manualmente citas y vigencia jurídica de los fragmentos recuperados antes de tratarlos como fundamentos confirmados. | Bitácora S4, S5, S6, S7 | Alta | Post-MVP | ⬜ Abierto |
| J-09 | Completar evaluación semántica formal del retriever con conjunto fijo de preguntas, fragmentos esperados y criterio explícito de corrección. El Precision@5 = 40% actual es preliminar y de una sola pregunta. | Bitácora S5 | Alta | S9 si hay tiempo; si no, post-MVP | ⬜ Abierto |
| J-10 | Inventariar y clasificar todas las tablas/cuadros de los dos programas urbanos. En PPCU, la extracción textual identifica las Tablas 1–22 y 24 (no aparece Tabla 23); además de la Tabla 22, quedan 22 rótulos numerados por cotejar e integrar según su función. En PDDU, la extracción identifica Cuadros 1–17; priorizar Cuadro 15 (usos del suelo) y Cuadro 16 (normas sobre vialidad), sin omitir el inventario de los demás. Actualmente solo Tabla 22 PPCU está estructurada en `land_use_compatibility`. | Bitácora S3, S5 + inventario preliminar de extracción 11-nov-2026 | Alta | S9 | ⬜ Abierto — inventario preliminar; pendiente cotejo visual y clasificación |
| J-11 | No inferir permisos, prohibiciones ni condiciones en `land_use_compatibility`. Conservar estados literales (`permitido`, `prohibido`, `por validar`) y procedencia (archivo, páginas). | Bitácora S5 | Regla permanente | — | ✅ Activa |
| J-12 | Conservar `needs_review = true` y `pendiente_revision: true` en los 1,235 chunks y 1,369 embeddings. No filtrar automáticamente. | Bitácora S4, S5 | Regla permanente | — | ✅ Activa |
| J-13 | Revisar precisión de metadatos documentales: los programas urbanos usan secciones decimales (4.3.1) que no equivalen a artículos jurídicos tradicionales. No etiquetar automáticamente como artículo. | Bitácora S5, nota de arquitectura | Media | Post-MVP | ⬜ Abierto |
| J-14 | Revisar si la arquitectura actual de tablas es la más adecuada (múltiples tablas en PPCU y PDU Cuauhtémoc). No rediseñar ahora; solo evaluar después del MVP. | Bitácora S5, nota de arquitectura | Baja | Post-MVP | ⬜ Abierto |
| J-15 | Validar los documentos fuente y su procedencia antes de corregir derivados. Usar como referencia de trabajo la rama `mvp-estancia`; registrar SHA, versión, páginas y correspondencia entre PDF, texto extraído, texto revisado y JSON. Los PDF y archivos `*_extracted.txt` tienen el mismo contenido/identificadores en `main` y `mvp-estancia`, pero los JSON difieren entre ramas. | Auditoría GitHub 11-nov-2026 | Alta | S9 | ⬜ Abierto — archivos identificados; falta cotejo visual de PDF |
| J-16 | Corregir el JSON de chunks del PPCU Hipódromo desde el documento fuente. El archivo de `mvp-estancia` contiene 52 registros: 49 tienen menos de 120 caracteres (principalmente encabezados sin desarrollo); dos concentran 118,611 y 231,134 caracteres. El índice del original contiene apartados ausentes del JSON, entre ellos 1.8 Usos del Suelo, 1.14 Vivienda, 1.22.1, 1.22.2, 3.4.1, 3.6, 3.10 y 4.2. El registro `29.90` parece provenir de un porcentaje de la Tabla 19, no de una sección. | PPCU PDF/extracción y `PPCU_Hipodromo_reviewed_chunks.json`, auditoría 11-nov-2026 | Bloqueante para embeddings PPCU | S9 | ⬜ Abierto |
| J-17 | Auditar visual y jurídicamente la Tabla 22 PPCU antes de modificar `land_use_compatibility`. El JSON tiene 51 actividades y 357 celdas: 31 permitido, 128 prohibido y 198 por validar; 30 actividades tienen al menos una celda por validar y 28 tienen las siete zonificaciones por validar. Los 51 registros mantienen `needs_review=true`. Verificar correspondencia de columnas, símbolos, notas y páginas 80–81 del PDF; no inferir ni completar estados. | `PPCU_Hipodromo_tabla_22.json` en `mvp-estancia` + extracción, auditoría 11-nov-2026 | Bloqueante para afirmar compatibilidad | S9 | ⬜ Abierto — conteo JSON confirmado; falta cotejo visual y jurídico |
| J-18 | Extraer, inventariar y estructurar las demás tablas del PPCU Hipódromo. La extracción textual identifica rótulos Tabla 1–22 y Tabla 24; no se localizó Tabla 23 mediante búsqueda literal. Este inventario es preliminar: cotejar visualmente numeración, títulos, páginas y continuidad en el PDF antes de concluir cuántas tablas existen o cuántas faltan por integrar. No asumir que todas deben convertirse en tablas de compatibilidad. | PPCU PDF/extracción, auditoría 11-nov-2026 | Alta | S9 | ⬜ Abierto |
| J-19 | Inventariar y estructurar los cuadros del PDDU Cuauhtémoc. La extracción identifica Cuadros 1–17; no existe actualmente un JSON estructurado de cuadros en `leyes_cdmx` en la rama `mvp-estancia`. Clasificar cada cuadro por función y priorizar Cuadro 15 (usos del suelo) y Cuadro 16 (normas de ordenación sobre vialidad). | PDDU PDF/extracción + árbol Git de `mvp-estancia`, auditoría 11-nov-2026 | Alta | S9 | ⬜ Abierto |
| J-20 | Corregir la extracción/chunking del PDDU Cuauhtémoc. El índice original incluye 1.2.3–1.2.11, 1.3 Pronóstico, 1.4, 1.5, 4.1–4.5 y 6.1–6.2.7, ausentes del JSON actual. El JSON contiene solo 13 registros; tres superan 8,000 caracteres y el máximo alcanza 594,660. La etiqueta `1.43` no aparece como apartado en el índice: coincide con el valor estadístico `-1.43` de la página 19 y parece un falso encabezado. La sección 1.3 sí existe en el original. | PDDU PDF/extracción y `PDDU-CUAUHTÉMOC_reviewed_chunks.json`, auditoría 11-nov-2026 | Bloqueante para embeddings PDDU | S9 | ⬜ Abierto |
| J-21 | Rediseñar la segmentación de programas urbanos para respetar su jerarquía documental y unidades de sentido: título, capítulo, apartado, sección, disposición, tabla/cuadro, fila, nota y zonificación. Separar el registro fuente de la unidad vectorial; cualquier división por longitud debe conservar contexto y no cortar relaciones entre encabezados, reglas, condiciones o celdas. | Hallazgos de `legal_document_processor.py` y `generar_embeddings.py` + auditoría 11-nov-2026 | Alta | S9 | ⬜ Abierto |
| J-22 | Integrar la recuperación estructurada de tablas al flujo de consulta. `retrieve_land_use()` existe de forma independiente y consulta Tabla 22, pero no está conectada al flujo `lambda_handler` → `answer_question()`. Definir extracción de actividad/zonificación, evidencia estructurada y su presentación/citación, sin tratar la tabla como embeddings. | Auditoría estática de Lambda/retriever 11-nov-2026 | Alta | S9 | ⬜ Abierto |
| J-23 | Verificar cobertura y diversidad del retriever sobre los cinco instrumentos. La búsqueda vectorial es global, pero limita candidatos antes del reranking y no garantiza cuota ni cobertura por documento. Crear pruebas por fuente y consultas que requieran una o varias fuentes; distinguir búsqueda global de cobertura demostrada. | Auditoría estática de `retriever.py` y pruebas 11-nov-2026 | Alta | S9 | ⬜ Abierto |
| J-24 | Mantener separadas las métricas de recuperación semántica, consulta estructurada de tablas y generación de respuestas. Definir preguntas esperadas, fuentes/disposiciones correctas y revisión jurídica humana; incluir regresión para tablas y continuidad de secciones. | Protocolo de evaluación S5 + auditoría 11-nov-2026 | Alta | S9 | ⬜ Abierto |

---

## 4. Pendientes de infraestructura y operación

| ID | Descripción | Origen | Estado |
|---|---|---|---|
| I-01 | Diseñar y documentar procedimiento seguro de control de costos: qué recursos detener, cuáles conservar, cómo reconstruir. AWS Budgets y Cost Anomaly Detection activos. | Bitácora S3, sección 10 | 🟡 Parcial (scripts `dev-up/status/down` existen; falta documentar estrategia completa) |
| I-02 | Antes de apagar DEV: conservar `salida/embeddings_mvp.jsonl`, chunks fuente, JSON estructurados de tablas, y verificar que `terraform/base` permanece intacto. | Bitácora S3, S5 | ⬜ Abierto como checklist |
| I-03 | Implementar ingesta directa desde S3 (el cargador actual solo lee archivo local `salida/embeddings_mvp.jsonl`). | Bitácora S4, limitación | ⬜ Abierto |
| I-04 | Documentar en `Instructivo_operacion.md` la secuencia completa de reconstrucción de DEV: `dev-up` → `init_db.sh` → `load_embeddings.py` → pruebas → `dev-down`. | Bitácora S5 | 🟡 Parcial (mencionado, verificar completitud) |
| I-05 | Verificar que tras `dev-down` los recursos de `terraform/base` (S3, IAM) permanecen intactos. | Bitácora S3 | ⬜ Abierto como checklist recurrente |
| I-06 | Revisar que la contraseña de Aurora se recupere siempre de Secrets Manager después de reconstruir DEV (no asumir vigencia de credenciales anteriores). | Bitácora S3 | ✅ Regla documentada; verificar en cada reconstrucción |
| I-07 | Confirmar que los VPC endpoints (`bedrock-runtime`, `secretsmanager`, `logs`) siguen activos y que no hay NAT Gateway. | Bitácora S7 | ⬜ Abierto como checklist |
| I-08 | Revisar si la API sin autenticación debe mantenerse así al cierre del MVP o si se agrega un control mínimo. | Bitácora S7 | ⬜ Abierto — requiere decisión del usuario |

---

## 5. Pendientes de documentación y control de versiones

### Fuente maestra y sincronización documental (regla vigente desde 10-nov-2026)

- `Contexto/Bitacora.md` es la fuente maestra de la bitácora.
- `Contexto/Instructivo_operacion.md` es la fuente maestra del instructivo.
- `Agente/AGENTS.md` y `Agente/ajustes_pendientes.md` son los documentos maestros de operación del agente y pendientes.
- Los cuatro archivos homónimos en la raíz de la rama `mvp-estancia` de GitHub deben contener la misma versión que los documentos maestros de la Biblioteca.
- Actualizar primero la copia de la carpeta de control correspondiente y sincronizar después GitHub. Conservar exactamente los nombres `Bitacora.md`, `Instructivo_operacion.md`, `AGENTS.md` y `ajustes_pendientes.md`.
- No crear ni mantener como documentos activos variantes con sufijos como `_actualizada`, `_actualizado`, `(1)` o `(2)`. Antes de retirar una copia duplicada, integrar cualquier información exclusiva en la fuente maestra.
- No hacer commit/push desde un entorno local sin autorización expresa; la sincronización solicitada para esta normalización se realizará en la rama `mvp-estancia`.


| ID | Descripción | Origen | Estado |
|---|---|---|---|
| D-01 | Revisar el diff de `.gitignore` antes de versionar. | Bitácora 10-oct | ⬜ Abierto |
| D-02 | Inspeccionar `generar_embeddings.py` y `generar_embeddings_persistente.py` antes de decidir si se versionan. | Bitácora 10-oct | ⬜ Abierto |
| D-03 | Revisar archivos de `sql/` y `scripts/` antes de commit/push. | Bitácora 10-oct | ⬜ Abierto |
| D-04 | Actualizar `README.md` con comandos de operación (validar/cargar embeddings, generar JSONL completo). | Bitácora 12-oct | 🟡 Parcial |
| D-05 | Verificar que los reportes semanales S1–S7 estén subidos a Drive. | Bitácora + link Drive | ⬜ Abierto — requiere confirmación del usuario |
| D-06 | Verificar que `scripts/probar_retriever.py` y `scripts/evaluar_semana5.py` y `scripts/diagnostico_ranking.py` estén en el repo antes de S9. | Bitácora 18-oct | ⬜ Abierto |
| D-07 | Documentar en `Instructivo_operacion.md` el procedimiento de reconstrucción de API Gateway y Lambda. | Bitácora S7, pendiente #4 | ⬜ Abierto |
| D-08 | Revisar `git diff --check` y `git status` antes de cada commit; no hacer `git add .` automático. | Regla permanente | ✅ Activa |
| D-09 | Pedir autorización expresa del usuario antes de commit/push. | Regla permanente | ✅ Activa |

---

## 6. Pendientes post-MVP (trabajo futuro — NO implementar ahora)

Estos pendientes provienen del documento `Alcance_y_limitaciones_Proyecto_Ismael.docx`, columna "Dejarás para después de la semana 10", y de decisiones de la bitácora. **No se implementan durante el MVP.** Si el usuario los solicita, se registran aquí y se recuerda que están fuera de alcance.

| ID | Descripción | Origen |
|---|---|---|
| F-01 | Integración con WhatsApp Business (Meta Cloud API) + FSM de AgentesMX. | Alcance + Bitácora fase 3 |
| F-02 | Panel administrativo para abogados y líderes vecinales. | Alcance |
| F-03 | Sistema de seguimiento de denuncias (hitos, notificaciones SES/SNS). | Alcance |
| F-04 | Alta disponibilidad Multi-AZ y plan formal de continuidad/recuperación ante desastres. | Alcance |
| F-05 | WAF + Shield y Object Lock para retención de evidencia legal. | Alcance |
| F-06 | Optimización de costos vía modelo escalonado (Haiku/Sonnet) y prompt caching. | Alcance |
| F-07 | Separación de ambientes staging/producción en Terraform (más allá de base/dev). | Alcance |
| F-08 | Reindexado por lotes con instancias EC2 Spot. | Alcance |
| F-09 | Conjunto completo de alarmas en CloudWatch (más allá de logs básicos). | Alcance |
| F-10 | Ampliar corpus más allá de los 5 instrumentos actuales (incorporar los 15 documentos restantes ya procesados). | Bitácora S1 |
| F-11 | Nuevas tablas `legal_tables`, `legal_table_rows`, `legal_embeddings` (esta última ya existe; las otras no crear sin validación). | Bitácora S3 |
| F-12 | Rediseño de arquitectura de tablas/cuadros normativos (múltiples tablas en PPCU y PDU Cuauhtémoc). | Bitácora S5 |
| F-13 | Migración a `mx-central-1` (región de México). | Bitácora fase 5 |
| F-14 | Simulacro de failover. | Bitácora fase 5 |
| F-15 | Ampliar la política de observabilidad y telemetría para producción: conservar logs operativos por un periodo superior a los 14 días del MVP; evaluar 90 días como retención inicial, sujeta a costos, finalidad y obligaciones aplicables. | Decisión del usuario, 10-nov-2026 |
| F-16 | Diseñar un registro de interacción para analítica de uso y perfilado agregado del usuario principal. En producción se requerirá registrar las preguntas y respuestas, además de metadatos técnicos mínimos (por ejemplo, sistema operativo, navegador y tipo de dispositivo derivados del User-Agent). Separar estos registros de los logs operativos de API Gateway/Lambda. | Decisión del usuario, 10-nov-2026 |

### 6.1 Ajustes de producción: seguridad, operación y calidad

| ID | Descripción | Origen / criterio |
|---|---|---|
| P-01 | Revisar y ajustar el throttling de API Gateway con datos de operación real y pruebas de carga. Partir del valor de referencia del MVP (5 req/s, burst 10), sin asumir que será adecuado para producción. | Acuerdo del usuario 10-nov-2026 |
| P-02 | Instrumentar en CloudWatch el seguimiento operativo del API y sus dependencias: volumen de solicitudes, respuestas 429 por throttling, errores 4xx/5xx, latencia, fallos y señales de saturación/capacidad. Definir métricas, dashboards y alarmas según necesidades y costos. | Acuerdo del usuario 10-nov-2026; ampliar F-09 |
| P-03 | Diseñar un proceso escalable y versionado de evaluación de calidad para el corpus legal completo (más de 20 instrumentos). Mantener un conjunto de referencia con preguntas por instrumento, materia y tipo de consulta; fuentes y disposiciones esperadas; casos sin evidencia suficiente; criterios de relevancia; y revisión humana de respuestas/citas. Reportar resultados globales y desglosados por instrumento, además de pruebas de regresión cada vez que se incorpore o actualice normativa. | Acuerdo del usuario 10-nov-2026 |
| P-04 | Definir control de versiones y trazabilidad entre versión del corpus, documentos normativos, chunking, embeddings, configuración del retriever, prompt y conjunto de evaluación, para que las comparaciones de calidad sean reproducibles. | Derivado de P-03 |
| P-05 | Establecer política de telemetría para operación posterior al MVP: datos recolectados, finalidad, minimización, anonimización, acceso, retención y mecanismo de información/consentimiento cuando corresponda. Mantener separados los logs operativos y los datos etiquetados para evaluación. | S9-11; acuerdo del usuario 10-nov-2026 |

### Requisitos de diseño para F-15 y F-16 (posterior a Semana 10)

- **Retención:** tomar 90 días como hipótesis inicial para logs operativos y telemetría; confirmar el plazo definitivo con un análisis de costos, finalidad y obligaciones legales. La retención de 14 días se mantiene como configuración del MVP, salvo cambio aprobado dentro de su alcance.
- **Contenido de interacción:** conservar pregunta y respuesta solo en un repositorio de telemetría diseñado para ese propósito; no incorporarlas indiscriminadamente a los access logs de API Gateway ni a los logs generales de Lambda.
- **Metadatos técnicos:** evaluar captura de sistema operativo, navegador, versión mayor y categoría de dispositivo. Preferir atributos derivados y normalizados del User-Agent; evitar conservar el User-Agent completo si no es necesario. No recolectar huella digital del dispositivo.
- **Perfilado:** definir qué significa “usuario principal”, qué preguntas de producto se quieren responder y qué decisiones se tomarán con esos datos. Priorizar estadísticas agregadas y cohortes; no inferir atributos personales sensibles.
- **Minimización y seudonimización:** evitar nombres, correos, teléfonos, direcciones, identificadores publicitarios, IP completa y otros datos personales si no son indispensables. Usar identificadores seudónimos y separar cualquier dato de contacto que eventualmente se requiera.
- **Transparencia y control:** antes de activar la captura de preguntas/respuestas, revisar el aviso de privacidad, la finalidad, la base de tratamiento/consentimiento que corresponda, los mecanismos para ejercer derechos y el plazo de conservación conforme al marco mexicano aplicable.
- **Seguridad:** definir cifrado en tránsito y en reposo, acceso por roles y mínimo privilegio, auditoría de accesos, eliminación al vencer la retención y tratamiento de solicitudes de eliminación. No registrar credenciales, tokens, secretos ni encabezados de autorización.
- **Separación de datos:** mantener diferenciados (a) logs operativos y de seguridad, (b) contenido de conversaciones para analítica y (c) dataset de evaluación jurídica/RAG, que debe ser versionado, controlado y etiquetado por separado. Las conversaciones reales no se convierten automáticamente en benchmark.
- **Gobernanza:** documentar esquema, responsables, permisos, retención por tipo de dato, anonimización/agregación y procedimiento de respuesta a incidentes antes del despliegue productivo.

**Alcance:** F-15 y F-16 son requisitos de producción posteriores al cierre de Semana 10. No autorizan almacenar preguntas/respuestas durante el MVP ni ampliar ahora los campos de CloudWatch. Su implementación requiere diseño técnico y revisión de privacidad específicos, además de autorización del usuario.

---

## 7. Decisiones que NO deben revertirse

| ID | Decisión | Origen |
|---|---|---|
| DEC-01 | Corpus MVP = 5 instrumentos (no 2-3, no 20). | Bitácora S3 |
| DEC-02 | Rama de trabajo = `mvp-estancia` (no `main`). | Bitácora S2 |
| DEC-03 | `terraform/base` persistente + `terraform/dev` efímero. | Bitácora S3 |
| DEC-04 | Embeddings = `amazon.titan-embed-text-v2:0`, 1024 dimensiones. | Bitácora S4 |
| DEC-05 | Generación = Claude Sonnet 4.6, `us.anthropic.claude-sonnet-4-6`. | Bitácora S6 |
| DEC-06 | Un solo modelo generativo (sin escalonamiento Haiku/Sonnet). | Alcance |
| DEC-07 | No duplicar el sistema de chunking; reutilizar `legal_document_processor.py`. | Bitácora S3 |
| DEC-08 | Corregir metadatos en el procesador, no en el JSON de salida. | Bitácora S3 |
| DEC-09 | Conservar `needs_review` / `pendiente_revision`. | Bitácora S4, S5 |
| DEC-10 | No inferir permisos/prohibiciones en tablas de uso de suelo. | Bitácora S5 |
| DEC-11 | No crear `legal_tables` ni `legal_table_rows` sin validación previa. | Bitácora S3 |
| DEC-12 | No regenerar embeddings si el artefacto correcto existe. | Bitácora S3 |
| DEC-13 | API sin autenticación es limitación conocida del MVP, no apta para producción; la autenticación se programa para Semana 10. | Bitácora S7 + acuerdo 10-nov-2026 |
| DEC-14 | Throttling inicial de referencia para las pruebas del MVP: 5 solicitudes por segundo y burst 10; no constituye dimensionamiento definitivo para producción. | Acuerdo del usuario 10-nov-2026 |
| DEC-15 | La evaluación de calidad comienza con el corpus MVP de cinco instrumentos, pero el diseño del proceso debe poder escalar al corpus legal completo (más de 20 instrumentos), con resultados por instrumento y pruebas de regresión. | Acuerdo del usuario 10-nov-2026 |

---

## 8. Datos consultados al usuario (registro)

Este apartado documenta los datos que faltaron y que se preguntaron al usuario, junto con la respuesta, para evitar preguntar lo mismo dos veces.

| Fecha | Dato faltante | Respuesta del usuario |
|---|---|---|
| (por registrar) | Estructura del frontend (vanilla vs framework) | Pendiente de definir en S8 |
| (por registrar) | Formato de presentación de citas en UI | Pendiente de definir en S8 |
| (por registrar) | ¿Mostrar `pendiente_revision` al usuario final? | Pendiente de definir en S8 |
| 10-nov-2026 | ¿Cuándo abordar autenticación de la API? | Incorporarla en Semana 10; no adelantarla a Semana 9. |
| 10-nov-2026 | ¿Qué throttling adoptar para pruebas y cómo tratarlo en producción? | Usar 5 req/s y burst 10 como punto de partida del MVP; en producción observar comportamiento mediante CloudWatch y ajustar con datos reales y pruebas de carga. |
| 10-nov-2026 | ¿Cómo plantear la evaluación de calidad ante la ampliación del corpus? | Recuperar ahora la evaluación con los cinco instrumentos del MVP, diseñándola desde el inicio para escalar a más de 20 instrumentos y permitir análisis por instrumento y regresiones. |

---

## 9. Historial de pendientes cerrados

| ID | Descripción | Cerrado en | Evidencia |
|---|---|---|---|
| — | Preprocesamiento y chunking del corpus | Semana 1–2 | `legal_document_processor.py`, 1,235 chunks |
| — | Infraestructura base AWS (VPC, subredes, S3, IAM) | Semana 2 | `terraform/base`, `Apply complete!` |
| — | Aurora PostgreSQL Serverless v2 + pgvector | Semana 3 | `psql` verificado, `vector 0.8.2` |
| — | Separación `terraform/base` y `terraform/dev` | Semana 3 | `dev-up/down/status` probados |
| — | Carga de 1,235 chunks y 1,369 embeddings | Semana 4 | `salida/embeddings_mvp.jsonl` cargado |
| — | Retriever híbrido + `land_use_compatibility` (Tabla 22) | Semana 5 | 357 celdas cargadas, pruebas documentadas |
| — | Generación de respuestas con citas | Semana 6 | Commit `85d7377`, 6 pruebas offline |
| — | Backend serverless + API Gateway | Semana 7 | Endpoint `https://1zhgtujka8.execute-api.us-east-1.amazonaws.com/consulta` |
| — | Frontend web estático, S3 privado, CloudFront y CORS de API Gateway | Semana 8 | URL `https://d3oqt1m39hvkdh.cloudfront.net`; distribución `E34XFAO1L3C0JJ`; prueba pública confirmada por el usuario |

---

## 10. Próxima acción

La siguiente tarea se realizará con un agente de programación en VS Code (Kilo Code o GitHub Copilot), con AWS apagado. El agente trabajará primero sobre el PPCU Hipódromo y no pasará al PDDU hasta cerrar y validar esta auditoría inicial.

1. Confirmar rama `mvp-estancia`, consultar `git status` y `git diff`; no descartar, sobrescribir ni incluir cambios locales ajenos a esta tarea. No ejecutar Terraform ni comandos que activen AWS.
2. Identificar y registrar SHA, tamaño, páginas y procedencia de `leyes_cdmx/PPCU_Hipodromo.pdf`, `PPCU_Hipodromo_extracted.txt`, `PPCU_Hipodromo_reviewed.txt` (si existe), `PPCU_Hipodromo_reviewed_chunks.json` y `PPCU_Hipodromo_tabla_22.json`. No usar `main` como fuente de trabajo ni mezclar archivos entre ramas.
3. Abrir el PDF original y cotejar visualmente el índice (inicialmente páginas 2–3, verificando la numeración real del visor) con los encabezados del texto extraído, texto revisado y JSON. Crear una matriz de correspondencia con: número de sección, título literal, página impresa, página PDF, presencia en cada derivado y observaciones.
4. Identificar y clasificar todos los rótulos de tablas/cuadros que aparezcan en el PDF. Registrar número, título literal, página(s), continuidad, notas, encabezados y si el contenido es tabla, figura, mapa o cuadro. Investigar expresamente la aparente ausencia de Tabla 23 y cualquier diferencia con el inventario preliminar de extracción; no dar por confirmado el total hasta recorrer el documento.
5. Entregar un informe de auditoría PPCU con evidencia de página y una lista priorizada de defectos. Distinguir errores confirmados, sospechas y puntos que requieren criterio jurídico. No corregir ni completar valores normativos por inferencia.
6. En esta primera fase no modificar el PDF original, el JSON de chunks, el JSON de Tabla 22, los embeddings, SQL ni el procesador. Primero presentar la matriz e informe para validación del usuario. Después de esa validación, proponer correcciones concretas y aplicarlas únicamente con autorización.
7. Una vez aprobado el inventario, cotejar la Tabla 22 página por página, incluidas filas, columnas, símbolos, notas y zonificaciones; mantener `por validar` y `needs_review=true` donde no exista evidencia inequívoca.
8. Solo después de cerrar el PPCU, repetir el mismo método para el PDDU Cuauhtémoc; luego corregir extracción/JSON, rediseñar chunking, regenerar embeddings e integrar recuperación estructurada, siguiendo los pendientes J-19 a J-24.

El agente debe trabajar paso a paso, mostrar archivos y diferencias antes de editar, y esperar aprobación humana para cambios de contenido legal. No hacer commit/push desde VS Code salvo autorización expresa; la actualización documental de este archivo se realiza por la sincronización maestra aprobada por el usuario.

### Criterios de aceptación de la auditoría de fuentes

- Cada PDF tiene versión, SHA, número de páginas y procedencia identificados.
- El índice y la secuencia de secciones de cada programa están cotejados contra el original.
- Cada tabla/cuadro tiene número, título, páginas y clasificación funcional.
- Cada celda estructurada conserva el valor literal del original, su nota y su página; las dudas permanecen como `por validar`.
- No existen chunks vacíos o de solo encabezado usados como evidencia, ni chunks gigantes sin segmentación semántica.
- No se generan embeddings a partir de fuentes o JSON cuya integridad no haya sido validada.
- La auditoría no equivale a validación jurídica de vigencia o aplicabilidad; esta requiere revisión especializada.

### Estado de ejecución

- Pruebas unitarias offline: 35 aprobadas, 1 warning de compatibilidad de pytest; sin fallos.
- DEV/AWS: apagado y sin recursos DEV registrados según `dev-status.sh`.
- Auditoría estática inicial de JSON: realizada el 11-nov-2026; los hallazgos J-16, J-17 y J-20 siguen abiertos hasta cotejo visual con los PDF.
- No regenerar embeddings, modificar SQL, cargar datos ni levantar AWS antes de completar los pasos previos y recibir autorización.