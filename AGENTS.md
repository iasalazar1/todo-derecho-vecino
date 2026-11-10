# AGENTS.md - Guía de Operación para el Agente de IA
# Proyecto: Todo Derecho Vecino — MVP de estancia (INFOTEC–CENIDET)

## 0. Lectura obligatoria antes de actuar

Antes de ejecutar cualquier acción, lee en este orden las fuentes maestras de la Biblioteca:
1. `Agente/AGENTS.md` — reglas de operación y control documental.
2. `Contexto/Bitacora.md` — estado real del proyecto, decisiones y cronología.
3. `Contexto/Instructivo_operacion.md` — operación, despliegue y reconstrucción.
4. `Agente/ajustes_pendientes.md` — memoria a largo plazo, pendientes y bloqueos.
5. `documentos_config.json` del repositorio — corpus y metadatos.

Después compara los cuatro documentos de control con sus espejos de la raíz de GitHub en `mvp-estancia`. Si no coinciden, primero integra las diferencias y sincroniza; no continúes con trabajo técnico usando copias divergentes.

Si un dato no está en estos archivos, **pregunta al usuario**. No inventes.

---

## 1. Contexto y estado actual del proyecto

**Repositorio:** `https://github.com/iasalazar1/todo-derecho-vecino`
**Rama de trabajo:** `mvp-estancia` (NO trabajar en `main`)
**Fase actual:** Semana 8 completada (frontend estático en S3/CloudFront y prueba pública confirmada por el usuario). Semana 9 (integración E2E, seguridad, observabilidad y evaluación de calidad) es la siguiente etapa, pendiente de ejecución paso a paso.
**Entorno:** AWS `us-east-1`, cuenta `857385469837`.

### Lo que YA está construido (no reconstruir desde cero)
- **Preprocesamiento:** `legal_document_processor.py` con chunking por artículo/fracción, `autoridad_ner.py`, `procedimiento_ner.py`.
- **Corpus MVP (5 instrumentos):**
  1. `PPCU_Hipodromo_reviewed.txt`
  2. `PDDU-CUAUHTÉMOC_reviewed.txt`
  3. `LEY_DE_ESTABLECIMIENTOS_MERCANTILES_PARA_LA_CDMX_5.4_reviewed.txt`
  4. `LEY_DE_DESARROLLO_URBANO_DEL_DF_5.1_reviewed.txt`
  5. `LEY_DE_CULTURA_CIVICA_DE_LA_CIUDAD_DE_MEXICO_2.8_reviewed.txt`
- **Chunks:** 1,235 chunks, 1,369 segmentos de embeddings.
- **Embeddings:** `amazon.titan-embed-text-v2:0`, 1024 dimensiones.
- **Modelo generativo:** Claude Sonnet 4.6, `us.anthropic.claude-sonnet-4-6`.
- **Esquema SQL:** `sql/001_initial_schema.sql` con `legal_documents`, `legal_chunks`, `legal_embeddings`.
- **Tabla estructurada:** `land_use_compatibility` (Tabla 22 del PPCU, 357 celdas).
- **Scripts existentes:** `retriever.py`, `generar_respuesta.py`, `generar_embeddings.py`, `generar_embeddings_persistente.py`, `scripts/load_embeddings.py`, `scripts/init_db.sh`, `scripts/responder_cli.py`, `prompts/respuesta_legal.txt`.
- **Infraestructura:** `terraform/base` (persistente) y `terraform/dev` (efímera).
- **Backend:** Lambda `todo-derecho-vecino-api` + API Gateway HTTP, ruta `POST /consulta`.
- **Endpoint publicado:** `https://1zhgtujka8.execute-api.us-east-1.amazonaws.com/consulta`.

### Lo que FALTA (semanas 9–10)
- Semana 9: pruebas E2E; revisión IAM de mínimo privilegio; logs básicos y revisión de datos registrados en CloudWatch; throttling y decisión de autenticación; evaluación reproducible del retriever y revisión humana de respuestas/citas; política mínima de telemetría y privacidad.
- Semana 10: corrección de hallazgos aprobados; arquitectura final; demo; verificación de los 10 reportes semanales y cierre documental.

**NO empieces desde la Semana 1.** La Semana 8 está cerrada; el proyecto está preparado para iniciar Semana 9 cuando el usuario lo indique.

---

## 2. Directrices de comportamiento estrictas

1. **Cero alucinaciones:** Si falta un dato (credencial, nombre de tabla, fragmento de ley, configuración, URL, dimensión de embedding), **detente y pregunta al usuario**. No inventes endpoints, variables, nombres ni fragmentos legales.
2. **Memoria persistente:** Todo lo relevante (decisión de diseño, comando que falló, idea futura, bloqueo, credencial pendiente) **debe registrarse inmediatamente en `ajustes_pendientes.md`**. Si no está ahí, se pierde.
3. **No inferir datos jurídicos:** No conviertas `por validar` en `permitido`/`prohibido`. No infieras aplicabilidad de tablas. No completes celdas ausentes. Conserva siempre el estado literal de la fuente.
4. **Conservar `needs_review` / `pendiente_revision`:** No filtres, no limpies, no marques como revisado sin autorización explícita del usuario.
5. **Distinguir preliminar de final:** Si una métrica (ej. Precision@5 = 40%) corresponde a una sola pregunta, no la presentes como métrica global. Documenta siempre el alcance de la evidencia.
6. **Revisar diff antes de commit/push:** No hacer `git add .` automáticamente. Revisar `git status` y `git diff --check`. Solo commit/push con autorización expresa del usuario.

---

## 3. Infraestructura: persistente vs. efímera (CRÍTICO)

### `terraform/base` — PERSISTENTE
- Bucket S3 `todo-derecho-vecino-857385469837-us-east-1` (documentos fuente).
- Rol IAM `TodoDerechoVecino-TerraformDeployRole`.
- `prevent_destroy = true` en S3 e IAM.
- **NUNCA destruir ni modificar `base` durante pruebas de DEV.**

### `terraform/dev` — EFÍMERA
- Aurora PostgreSQL Serverless v2 + pgvector.
- VPC, subredes privadas, Security Groups.
- EC2 temporal `admin_test` + VPC endpoints SSM.
- **`./terraform/dev-down.sh` destruye DEV y TODOS los datos de Aurora** (tablas, chunks, embeddings).
- **Antes de apagar DEV:** conservar artefactos fuera de Aurora (S3, local, `salida/embeddings_mvp.jsonl`).

### Scripts de operación (usar estos, no `terraform` directo)
- `./terraform/dev-up.sh` — enciende DEV.
- `./terraform/dev-status.sh` — verifica estado.
- `./terraform/dev-down.sh` — apaga y destruye DEV.
- Tras reconstruir DEV: **recrear/verificar esquema** (`scripts/init_db.sh`) y **recargar embeddings** (`scripts/load_embeddings.py`).

### Control de costos
- Apagar DEV (`dev-down.sh`) cuando no se trabaje.
- AWS Budgets y Cost Anomaly Detection activos.
- Registrar en bitácora cada encendido/apagado y verificar estado final.

---

## 4. Acceso, red y credenciales

- **Aurora no es accesible públicamente.** El acceso es vía:
  1. EC2 `admin_test` + SSM Session Manager (port forwarding).
  2. Túnel local: `aws ssm start-session --target i-04a1bd28964bbf829 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["<aurora-endpoint>"],"portNumber":["5432"],"localPortNumber":["5432"]}'`
  3. `psql -h localhost -p 5432 -U tdv_admin -d tododerechovecino`
- **Credenciales:** `manage_master_user_password = true`. La contraseña está en **AWS Secrets Manager**, no en Terraform.
- **NO imprimir contraseñas**, no commitear `.pgpass`, no pasar contraseñas como argumentos de proceso.
- **Después de reconstruir Aurora, la contraseña anterior deja de ser válida.** Recuperar el secreto vigente.
- **VPC endpoints** (sin NAT Gateway): `bedrock-runtime`, `secretsmanager`, `logs`.
- **Python:** ejecutar scripts desde `.venv` activo.

---

## 5. Modelos y esquema de datos

- **Embeddings:** `amazon.titan-embed-text-v2:0`, 1024 dimensiones.
- **Generación:** Claude Sonnet 4.6, `us.anthropic.claude-sonnet-4-6`, `us-east-1`.
- **No regenerar embeddings** si el artefacto correcto ya existe (`salida/embeddings_mvp.jsonl`).
- **Esquema existente:** `legal_documents`, `legal_chunks`, `legal_embeddings`, `land_use_compatibility`.
- **No crear tablas nuevas** (`legal_tables`, `legal_table_rows`, etc.) sin validación previa y autorización.
- **No duplicar el sistema de chunking.** Reutilizar `legal_document_processor.py`.

---

## 6. Reglas de calidad jurídica

1. **No inferir permisos, prohibiciones ni condiciones** que no estén explícitamente en la fuente.
2. **Conservar estado literal:** `permitido`, `prohibido`, `por validar` son valores originales. No reemplazarlos.
3. **Conservar procedencia:** páginas, archivo fuente, referencia, `cita_legal`.
4. **Corregir en el procesador, no en el JSON de salida.** Si un metadato está mal (ej. título de PDDU), corregir `legal_document_processor.py` y regenerar.
5. **Toda respuesta debe incluir al menos una cita normativa** verificable.
6. **Reconocer evidencia insuficiente:** si el corpus no respalda una respuesta, el sistema debe decirlo, no inventar.

---

## 7. Archivos de control obligatorios y fuente maestra

Los documentos de control tienen una ubicación canónica en la Biblioteca del proyecto. **No se deben buscar ni actualizar copias alternativas antes de consultar estas rutas:**

1. `Contexto/Bitacora.md` — registro cronológico del proyecto.
2. `Contexto/Instructivo_operacion.md` — procedimientos operativos y de reconstrucción.
3. `Agente/ajustes_pendientes.md` — memoria de pendientes, decisiones y bloqueos.
4. `Agente/AGENTS.md` — reglas de trabajo del agente.
5. `Reporte_Semanal_XX.md` — reporte de cada semana, con el formato de la sección 8. Subir a Google Drive: `https://drive.google.com/drive/folders/1-f1tkBKLP7c8aZo-IU9_Zb3ME4CEIB9K`.

### 7.1 Regla obligatoria de actualización y sincronización

- Las carpetas `Contexto` y `Agente` de la Biblioteca son la **fuente maestra** de los documentos de control. `Contexto` gobierna `Bitacora.md` e `Instructivo_operacion.md`; `Agente` gobierna `AGENTS.md` y `ajustes_pendientes.md`.
- Los archivos con esos mismos nombres en la raíz de la rama `mvp-estancia` de GitHub son el espejo versionado y deben mantenerse sincronizados con la fuente maestra.
- Toda actualización se realiza primero en la carpeta de control correspondiente; después se actualiza la copia de GitHub con el mismo contenido.
- Conservar siempre los nombres originales exactos: `Bitacora.md`, `Instructivo_operacion.md`, `ajustes_pendientes.md` y `AGENTS.md`. **Está prohibido crear o utilizar como versión activa** nombres como `Bitacora_actualizada.md`, `ajustes_pendientes_actualizado.md`, `Instructivo_operacion(2).md` u otras variantes con sufijos.
- Si se encuentran varias copias, comparar fechas y contenido, integrar la información exclusiva y conservar la versión más reciente y completa. No sobrescribir ni eliminar una copia hasta verificar que sus datos útiles quedaron integrados en la fuente maestra.
- Después de actualizar, comprobar que Biblioteca y GitHub contienen los mismos contenidos y registrar la sincronización en `Bitacora.md`.
- Esta regla no elimina la autorización explícita necesaria para cambios de código, infraestructura, ni para operaciones Git locales no solicitadas por el usuario.

---

## 8. Formato obligatorio del reporte semanal

- **Semana No. y fechas**
- **Qué se hizo**
- **Cómo se hizo** (decisiones técnicas y por qué)
- **Problemas identificados**
- **Cómo se resolvieron**
- **Evidencia / entregable de la semana** (repo, capturas, URLs, comandos)
- **Estado frente al cronograma** (a tiempo / adelantado / con retraso)

---

## 9. Cronograma restante (semanas 8–10)

### Semana 8 — Frontend web (COMPLETADA, 9-nov-2026)
- Frontend estático HTML/CSS/JS publicado en S3 privado y CloudFront.
- Conexión al endpoint `POST /consulta` y CORS configurado.
- El usuario confirmó una consulta correcta desde el dominio público.
- La prueba acredita el caso técnico probado, no calidad global del RAG ni validez jurídica.

### Semana 9 — Integración, pruebas y hardening
- Pruebas E2E.
- Revisión de permisos IAM (mínimo privilegio).
- Activar logs básicos en CloudWatch.
- **Entregable:** sistema estable desplegado con logs.

### Semana 10 — Cierre y entrega funcional
- Corregir hallazgos de Semana 9.
- Documentar arquitectura final.
- Demo funcional.
- **Entregable:** MVP completo (web + RAG + citas) desplegado, documentación técnica, 10 reportes semanales.

---

## 10. Límites estrictos del alcance (NO HACER en el MVP)

- ❌ WhatsApp Business / FSM de AgentesMX (Fase 3 del roadmap, en pausa).
- ❌ Panel administrativo para abogados/líderes.
- ❌ Sistema de seguimiento de denuncias (SES/SNS).
- ❌ Alta disponibilidad Multi-AZ o plan de DR.
- ❌ WAF + Shield y Object Lock.
- ❌ Escalonamiento de modelos (Haiku/Sonnet) ni prompt caching.
- ❌ Separación staging/producción (ya existe base/dev, no agregar más).
- ❌ Reindexado con EC2 Spot.
- ❌ Conjunto completo de alarmas en CloudWatch.
- ❌ Nuevas tablas (`legal_tables`, `legal_table_rows`) sin validación.
- ❌ Ampliar el corpus más allá de los 5 instrumentos definidos.
- ❌ Regenerar embeddings si el artefacto correcto existe.

Cualquier funcionalidad de esta lista que el usuario pida se registra en `ajustes_pendientes.md` como trabajo futuro, **no se implementa ahora**.

---

## 11. Antipatrones conocidos (evitar)

1. **`git add .` automático** → revisar diff primero.
2. **Commit/push sin autorización** → siempre pedir confirmación.
3. **Imprimir contraseñas o secretos** → usar Secrets Manager, no logs.
4. **Asumir que credenciales anteriores siguen vigentes** → recuperar secreto vigente tras reconstruir Aurora.
5. **Apagar DEV sin conservar artefactos** → pérdida de 1,235 chunks y 1,369 embeddings.
6. **Editar JSON de salida manualmente** → corregir en el procesador y regenerar.
7. **Filtrar `needs_review`** → conservar marcas.
8. **Presentar Precision@5 = 40% como métrica global** → es preliminar, una sola pregunta.
9. **Crear tablas nuevas sin validar** → autorización explícita.
10. **Duplicar el chunking** → reutilizar `legal_document_processor.py`.
11. **Asumir que pruebas offline demuestran conectividad** → no es así.
12. **Revivir la Fase 3 (WhatsApp)** → está en pausa.
13. **Ampliar el corpus** → son 5 instrumentos, no más.
14. **Reconstruir desde cero** → el proyecto ya está en Semana 8.

---

## 12. Definición de "Funcional" al cierre de Semana 10

- Un usuario escribe en el frontend y recibe respuesta con al menos una cita normativa.
- El flujo corre de punta a punta en AWS (no solo local).
- La infraestructura se reconstruye desde Terraform (`base` + `dev`).
- Logs básicos en CloudWatch activos.
- Evaluación del retriever documentada (preguntas, criterio, métrica) — **preliminar es aceptable, pero debe estar documentado su alcance**.
- 10 reportes semanales entregados y subidos a Drive.
- `Bitacora.md`, `Instructivo_operacion.md`, `ajustes_pendientes.md` actualizados y consistentes.

---

## 13. Modo de trabajo interactivo (REGLA OBLIGATORIA)

Esta sección sustituye y unifica los antiguos "Protocolo de arranque" y
"Protocolo de cierre". El agente **NO trabaja de forma autónoma por
semanas completas**. Debe guiar al usuario paso por paso y esperar
validación explícita antes de avanzar. Esta regla prevalece sobre
cualquier otra instrucción de "avanzar lo más posible".

### 13.1 Arranque de sesión y de semana

Al inicio de cada sesión o semana:

1. Leer este `Agente/AGENTS.md` y las versiones maestras de Biblioteca: `Contexto/Bitacora.md`, `Agente/ajustes_pendientes.md` y `Contexto/Instructivo_operacion.md`.
2. Comprobar que los archivos homónimos de la raíz del repositorio en GitHub corresponden a esas versiones. Si hay diferencias, detener el trabajo técnico, comparar e integrar antes de continuar.
3. Verificar rama: `git branch --show-current` debe ser `mvp-estancia`.
4. Verificar estado: `git status` y `git diff --check`.
5. Verificar estado de AWS: `./terraform/dev-status.sh` (si aplica).
6. Consultar `ajustes_pendientes.md`, sección 1 (bloqueantes) y sección 10 (próxima acción).
7. **Presentar al usuario un Plan de Trabajo Semanal estructurado** con:
   - Objetivo de la semana.
   - Entregable verificable.
   - Lista numerada de pasos propuestos.
   - Decisiones que requieren input del usuario (marcadas como
     `[REQUIERE TU DECISIÓN]`).
   - Riesgos y dependencias.
   - Criterio de cierre de la semana.
8. **Esperar aprobación explícita del usuario** antes de ejecutar
   cualquier paso. No asumir aprobación por silencio.

### 13.2 Ejecución paso a paso

Durante la semana:

1. Ejecutar **un paso a la vez**.
2. Al terminar cada paso, mostrar al usuario:
   - Qué se hizo.
   - Evidencia (comando, archivo, captura, salida).
   - Qué sigue.
3. **Esperar validación del usuario** antes del siguiente paso.
4. Si un paso falla, **detenerse y reportar** antes de intentar
   alternativas. No improvisar soluciones fuera del plan sin consultar.
5. Si surge un dato faltante, **preguntar al usuario** (regla 2.1) y
   registrar la respuesta en `ajustes_pendientes.md`, sección 8.
6. Si el paso implica cambio de infraestructura o de procedimiento de
   despliegue, actualizar `Instructivo_operacion.md` antes de continuar.
7. Mantener `Bitacora.md` actualizada al final de cada paso relevante
   (no solo al cierre de la semana).

### 13.3 Cierre de semana

1. Una vez completados los pasos del plan, **preguntar al usuario**:
   > "¿Damos por terminada la Semana N? Si es así, generaré el
   > `Reporte_Semanal_NN.md`, actualizaré `Bitacora.md` y
   > `ajustes_pendientes.md`, y prepararé la evidencia comprobatoria."
2. Solo si el usuario confirma:
   - Verificar que el entregable semanal esté completo.
   - Crear `Reporte_Semanal_NN.md` con el formato de la sección 8.
   - Actualizar `Bitacora.md` con la entrada de cierre de semana.
   - Mover pendientes cerrados a la sección 9 de `ajustes_pendientes.md`.
   - Actualizar `Instructivo_operacion.md` si hubo cambios técnicos.
   - Generar la evidencia comprobatoria (capturas, URLs, comandos,
     enlaces al repo).
   - Recordar al usuario subir el reporte a Drive
     (`https://drive.google.com/drive/folders/1-f1tkBKLP7c8aZo-IU9_Zb3ME4CEIB9K`).
   - Revisar `git diff --check` y `git status`.
   - **Pedir autorización expresa para commit/push** (no hacer `git add .`
     automático).
   - Si se usó AWS: apagar DEV (`./terraform/dev-down.sh`) y conservar
     artefactos (`salida/embeddings_mvp.jsonl`, chunks fuente, JSON de
     tablas) fuera de Aurora.
   - Confirmar que `terraform/base` permanece intacto.
   - Registrar el estado final de la semana en `Bitacora.md`.
3. **No avanzar a la siguiente semana** hasta que el usuario lo indique
   explícitamente.

### 13.4 Prohibiciones explícitas

- ❌ No ejecutar varias semanas en un solo sprint.
- ❌ No ejecutar varios pasos de una semana sin validación intermedia.
- ❌ No asumir que "el usuario quiere que avance lo más posible".
- ❌ No cerrar una semana sin preguntar.
- ❌ No generar reportes semanales sin confirmación.
- ❌ No hacer commit/push sin autorización expresa.
- ❌ No apagar DEV sin conservar artefactos fuera de Aurora.