# ajustes_pendientes.md
# Proyecto: Todo Derecho Vecino — MVP de estancia
# Última actualización: 9 de noviembre de 2026 — registro de mediciones de calidad para Semana 9
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
| B8-01 | Verificar que `scripts/probar_retriever.py` exista en el árbol de trabajo real del repo (fue mencionado en la bitácora del 18-oct pero no se confirmó su presencia). | Bitácora 18-oct, sección "Pendiente" | ⬜ Abierto | Si no existe, reconstruirlo antes de S9. |
| B8-02 | Confirmar estado operativo de AWS: ¿DEV está apagado o encendido? Verificar con `./terraform/dev-status.sh`. | Bitácora S7 y control de costos | ⬜ Abierto | Apagar si no se usará; recordar que Aurora es efímera. |
| B8-03 | Confirmar que el endpoint responde correctamente desde el frontend público. | Bitácora S7–S8 | ✅ Cerrado — 9-nov-2026 | El usuario confirmó una respuesta correcta desde CloudFront, similar a la prueba local. |
| B8-04 | Definir estructura del frontend. | Arquitectura MVP + alcance S8 | ✅ Cerrado — 9-nov-2026 | Se implementó frontend estático HTML/CSS/JavaScript, sin framework. |
| B8-05 | Definir con el usuario cómo se mostrarán las citas `[F1]`–`[F5]` en la UI: ¿inline en el texto, panel lateral, tooltip, lista al final? | Alcance S8 | ⬜ Abierto — requiere decisión del usuario | Recomendación: lista al final + referencias inline clickeables. |
| B8-06 | Definir si el frontend mostrará al usuario final el indicador `pendiente_revision: true` de cada fuente, o si se ocultará. | Bitácora S5, S7 | ⬜ Abierto — requiere decisión del usuario | Recomendación: mostrar aviso discreto de "fuente preliminar". |
| B8-07 | Definir si el frontend tendrá algún control de acceso básico (API key, header) o si se dejará abierto como el endpoint actual. | Bitácora S7 (limitación conocida) | ⬜ Abierto — requiere decisión del usuario | Si se deja abierto, registrar como limitación conocida del MVP. |

---

## 2. Pendientes técnicos para Semanas 8–10

### 2.1 Semana 8 (frontend)

| ID | Descripción | Estado | Notas |
|---|---|---|---|
| S8-01 | Construir interfaz de chat responsiva. | ✅ Completado — 9-nov-2026 | Frontend estático HTML/CSS/JS publicado en CloudFront. |
| S8-02 | Conectar frontend al endpoint `/consulta`. | ✅ Completado — 9-nov-2026 | Prueba pública desde CloudFront confirmada por el usuario. |
| S8-03 | Renderizar respuesta + citas `[F1]`–`[F5]`. | ✅ Completado técnicamente — 9-nov-2026 | La UI presenta respuesta y fuentes; revisión de escenarios y estados jurídicos pasa a S9. |
| S8-04 | Manejar errores HTTP (400, 404, 5xx) en la UI. | ⬜ Pendiente | — |
| S8-05 | Añadir indicador de carga mientras se espera respuesta. | ⬜ Pendiente | El timeout de Lambda es 28s. |
| S8-06 | Documentar el despliegue del frontend en `Instructivo_operacion.md`. | ✅ Completado — 9-nov-2026 | Sección 26: S3, CloudFront, CORS, verificación y distinción BASE/DEV. |
| S8-07 | Revisar y mejorar la interpretación y presentación de las respuestas de la API en el frontend, sin modificar inicialmente el contrato del backend. | ⬜ Pendiente — después de completar el flujo técnico | Validar con respuestas JSON reales los casos de respuesta con evidencia, citas pendientes de revisión, evidencia insuficiente y error técnico. Ver detalle abajo. |

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
| S9-03 | Activar logs básicos en CloudWatch para la Lambda (consultas entrantes, errores). | ⬜ Pendiente | Solo logs básicos, sin conjunto completo de alarmas. |
| S9-04 | Revisar throttling de API Gateway (5 req/s, burst 10). | ⬜ Pendiente | Ajustar si es necesario. |
| S9-05 | Decidir con el usuario si se aborda autenticación de la API en S9 o se deja como limitación del MVP. | ⬜ Pendiente — requiere decisión del usuario | Ver S7, "Seguridad de la API". |
| S9-06 | Documentar hallazgos de pruebas en `Bitacora.md` y `Reporte_Semanal_09.md`. | ⬜ Pendiente | — |
| S9-07 | Determinar y documentar qué datos de cada consulta quedan registrados actualmente en CloudWatch/Lambda/API Gateway; verificarlo en código y logs reales, sin asumir que existe un historial consultable de preguntas. | ⬜ Pendiente | Distinguir logs operativos de un dataset de evaluación. No afirmar que las consultas se almacenan para medir calidad hasta comprobarlo. |
| S9-08 | Definir un conjunto fijo y versionado de consultas de evaluación, separado de las consultas espontáneas de usuarios. | ⬜ Pendiente | Incluir preguntas representativas de los cinco instrumentos y casos de evidencia insuficiente; conservar pregunta, respuesta esperada, fuentes/disposiciones relevantes y criterio de corrección. |
| S9-09 | Medir calidad del recuperador sobre el conjunto fijo con `Precision@k` y `Recall@k` (y, si los datos esperados permiten ordenar relevancia, `MRR` o `nDCG@k`). | ⬜ Pendiente | Fijar k y la unidad evaluada (fragmento, disposición o documento) antes de correr la evaluación. El `Precision@5 = 0.40` de una pregunta sigue siendo solo un dato preliminar, no una línea base global. |
| S9-10 | Evaluar manualmente la calidad de respuestas generadas y sus citas con una rúbrica reproducible. | ⬜ Pendiente | Puntuar por separado: fidelidad a las fuentes recuperadas, exactitud/localización de citas, cobertura de aspectos solicitados, reconocimiento de evidencia insuficiente y ausencia de afirmaciones no sustentadas. Revisión humana; no confundir con métricas del retriever. |
| S9-11 | Definir una política mínima de telemetría y privacidad antes de registrar consultas reales para análisis. | ⬜ Pendiente | Determinar campos, retención, acceso y anonimización; evitar registrar datos personales o contenido sensible innecesario. No crear una tabla nueva ni persistir preguntas completas sin validar necesidad, consentimiento/aviso y diseño. |

#### Consideraciones para medir calidad en Semana 9

La prueba satisfactoria desde CloudFront del 9 de noviembre de 2026 acredita que el flujo público funciona técnicamente en el caso probado. **No acredita por sí sola la calidad global del RAG ni constituye una medición de score.** Las consultas hechas manualmente desde el navegador tampoco deben considerarse automáticamente un conjunto de evaluación.

Separar tres niveles de medición:

1. **Operación E2E:** registrar resultado HTTP, errores por etapa y latencia total (y, si está disponible, latencia de recuperación y generación). Reportar número de pruebas, éxitos/fallos y tasa de error. Esto mide disponibilidad y comportamiento técnico, no corrección jurídica.
2. **Recuperación:** ejecutar un conjunto fijo de preguntas con fragmentos/disposiciones relevantes etiquetados previamente. Calcular `Precision@k` y `Recall@k`; usar `MRR` o `nDCG@k` solo si se definió una escala de relevancia y el orden esperado. Reportar resultados por pregunta y agregados, además de fallos por instrumento. No mezclar la búsqueda semántica con la consulta estructurada de Tabla 22 en una sola métrica.
3. **Generación y citas:** aplicar una rúbrica de revisión humana a respuestas completas. Evaluar por separado fidelidad al contexto recuperado, correspondencia de cada cita con la fuente, cobertura, manejo de incertidumbre/evidencia insuficiente y afirmaciones no sustentadas. La vigencia y aplicabilidad normativa requieren revisión jurídica independiente.

**Estado de almacenamiento de consultas:** todavía no está verificado si el código de Lambda registra el texto de las preguntas, los resultados recuperados o las respuestas, ni si API Gateway conserva datos suficientes para reconstruir una consulta. CloudWatch Logs se contempla en S9-03 como registro básico de operación; eso no equivale a una base histórica etiquetada ni a un mecanismo de scoring. En S9-07 se inspeccionarán el código y los logs existentes antes de decidir si hace falta instrumentación adicional.

**Regla para datos reales:** no usar consultas espontáneas de usuarios como benchmark sin etiquetarlas y revisar su representatividad. Si se decide conservarlas, minimizar datos, evitar información personal/sensible, definir acceso y retención y documentar el aviso correspondiente. No almacenar el contenido completo de consultas por defecto ni crear tablas nuevas sin decisión y autorización.

**Resultado esperado de S9:** un informe que separe métricas operativas, métricas del retriever y evaluación humana de respuestas; indique tamaño y composición del conjunto, criterios, k, resultados por caso, limitaciones y pendientes jurídicos. Mantener `needs_review = true` / `pendiente_revision = true`.

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

---

## 3. Pendientes de calidad jurídica y de datos

| ID | Descripción | Origen | Prioridad | Semana objetivo | Estado |
|---|---|---|---|---|---|
| J-01 | Completar las URLs reales de la Gaceta Oficial en `documentos_config.json` (20 documentos con `"fuente": "PENDIENTE: URL..."`). Buscar en `data.consejeria.cdmx.gob.mx`. | Bitácora fase 1 | Media | Post-MVP o S9 | ⬜ Abierto |
| J-02 | Limpiar manualmente bloques de índice duplicados en PPCU Hipódromo (numeración 1.1 a 8.4 repetida en 3 pasadas). | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-03 | Regenerar JSON de PDDU-Cuauhtémoc con el título correcto. Actualmente dice "Programa Parcial de Desarrollo Urbano Hipódromo". Corregir en `legal_document_processor.py` y regenerar. | Bitácora S3 | Alta | S8–S9 | ⬜ Abierto |
| J-04 | Confirmar que las versiones de dos documentos son correctas: Ley Orgánica de Alcaldías (v6.1 config vs v6.4 archivo) y Reglamento LEM (v2 config vs v1 archivo). | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-05 | Validar `autoridad_ner.py` (spaCy + `es_core_news_sm`) en entorno local; confirmar que `sujetos_obligados` se llena correctamente. | Bitácora fase 1 | Media | Post-MVP | ⬜ Abierto |
| J-06 | Afinar heurística de `tipo_disposicion`: casi el 100% de fragmentos quedan `needs_review: true`. | Bitácora fase 1 | Baja | Post-MVP | ⬜ Abierto |
| J-07 | Revisión manual de calidad de chunks contra PDF original, prioridad PDDU/PPCU. | Bitácora fase 1 | Alta | Post-MVP | ⬜ Abierto |
| J-08 | Validar manualmente citas y vigencia jurídica de los fragmentos recuperados antes de tratarlos como fundamentos confirmados. | Bitácora S4, S5, S6, S7 | Alta | Post-MVP | ⬜ Abierto |
| J-09 | Completar evaluación semántica formal del retriever con conjunto fijo de preguntas, fragmentos esperados y criterio explícito de corrección. El Precision@5 = 40% actual es preliminar y de una sola pregunta. | Bitácora S5 | Alta | S9 si hay tiempo; si no, post-MVP | ⬜ Abierto |
| J-10 | Revisar tablas y cuadros normativos especiales: Tabla 20 PPCU ("Normatividad por vialidad"), Cuadro 15 PDDU ("Tabla de Usos del Suelo"), Cuadro 16 PDDU ("Normas de Ordenación sobre Vialidad"). Actualmente solo la Tabla 22 PPCU está en `land_use_compatibility`. | Bitácora S3, S5 | Alta | Post-MVP | ⬜ Abierto |
| J-11 | No inferir permisos, prohibiciones ni condiciones en `land_use_compatibility`. Conservar estados literales (`permitido`, `prohibido`, `por validar`) y procedencia (archivo, páginas). | Bitácora S5 | Regla permanente | — | ✅ Activa |
| J-12 | Conservar `needs_review = true` y `pendiente_revision: true` en los 1,235 chunks y 1,369 embeddings. No filtrar automáticamente. | Bitácora S4, S5 | Regla permanente | — | ✅ Activa |
| J-13 | Revisar precisión de metadatos documentales: los programas urbanos usan secciones decimales (4.3.1) que no equivalen a artículos jurídicos tradicionales. No etiquetar automáticamente como artículo. | Bitácora S5, nota de arquitectura | Media | Post-MVP | ⬜ Abierto |
| J-14 | Revisar si la arquitectura actual de tablas es la más adecuada (múltiples tablas en PPCU y PDU Cuauhtémoc). No rediseñar ahora; solo evaluar después del MVP. | Bitácora S5, nota de arquitectura | Baja | Post-MVP | ⬜ Abierto |

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
| DEC-13 | API sin autenticación es limitación conocida del MVP, no apta para producción. | Bitácora S7 |

---

## 8. Datos consultados al usuario (registro)

Este apartado documenta los datos que faltaron y que se preguntaron al usuario, junto con la respuesta, para evitar preguntar lo mismo dos veces.

| Fecha | Dato faltante | Respuesta del usuario |
|---|---|---|
| (por registrar) | Estructura del frontend (vanilla vs framework) | Pendiente de definir en S8 |
| (por registrar) | Formato de presentación de citas en UI | Pendiente de definir en S8 |
| (por registrar) | ¿Mostrar `pendiente_revision` al usuario final? | Pendiente de definir en S8 |
| (por registrar) | ¿Autenticación de la API en S9 o post-MVP? | Pendiente de definir en S9 |

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

---

## 10. Próxima acción

Al iniciar la Sesión de Semana 8, el Agente debe:

1. **Presentar un plan de trabajo estructurado** para la Semana 8 (ver `AGENTS.md`, sección 13).
2. **Esperar validación del usuario** antes de ejecutar cada paso.
3. **Resolver primero los BLOQUEANTES B8-01 a B8-07**, que requieren decisiones del usuario.
4. **No avanzar a Semana 9** sin que el usuario dé por cerrada la Semana 8.
5. **Al cierre de Semana 8:** preguntar al usuario si se da por terminada, generar `Reporte_Semanal_08.md`, actualizar `Bitacora.md` y `ajustes_pendientes.md`.