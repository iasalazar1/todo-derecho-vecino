

## Semana 10 — Plan de trabajo, control de avance y auditoría exhaustiva

**Fecha de registro:** 25 de noviembre de 2026  
**Rama:** `mvp-estancia`  
**Alcance de esta actualización:** registro documental del plan y del informe inicial de Cline. No acredita por sí mismo que las actividades técnicas descritas hayan sido ejecutadas o validadas de manera independiente.

### Objetivo de Semana 10

Consolidar el MVP de Todo Derecho Vecino mediante una revisión exhaustiva, reproducible y ordenada del corpus, sus artefactos derivados, la recuperación, las pruebas, la interfaz, la operación y la seguridad. El criterio rector es verificar cada punto y subpunto de la ruta de trabajo en orden, aunque varias tareas compatibles se agrupen en un mismo prompt de Cline. La agrupación de tareas no elimina la obligación de informar el resultado de cada punto por separado.

### Método de trabajo y control de avance

1. Cada paquete de trabajo deberá enumerar explícitamente los puntos y subpuntos que aborda.
2. Cline deberá marcar cada punto como **Comprobado**, **Parcial**, **Pendiente**, **Bloqueado** o **No aplica**, e incluir evidencia concreta: archivo/ruta, sección o identificador, comando ejecutado y resultado.
3. No se marcará un punto como completado por una inspección superficial, por la existencia de un archivo o por una afirmación sin evidencia reproducible.
4. Cuando una validación dependa de una fuente original, se cotejará contra esa fuente; los JSON, chunks, embeddings, informes anteriores y resúmenes no sustituyen al PDF o texto fuente.
5. Se preservarán los archivos originales, el historial y las marcas `needs_review`/`pendiente_revision`. No se inventará contenido ni se resolverán ambigüedades normativas por inferencia.
6. Se diferenciarán claramente las pruebas offline/mock, las pruebas locales con servicios reales, las pruebas AWS, las pruebas E2E y la revisión jurídica humana.
7. Se trabajará primero en local. No se ejecutarán invocaciones reales de Bedrock, cargas a Aurora, despliegues, cambios IAM/Terraform, modificaciones de API/frontend, commits/push ni destrucción/reconstrucción de DEV sin autorización específica.
8. Antes de cualquier modificación se revisarán la rama, el estado del árbol y el diff. Se preservará la eliminación local reportada de `tests/test_lambda_function.py` hasta conocer su origen y propósito; no se restaurará ni eliminará automáticamente.

### Ruta de trabajo ordenada

#### M1. Integridad de fuentes y procesamiento documental

**M1.1 PPCU Hipódromo**
- Cotejar el PDF fuente completo, el índice, el texto revisado y el JSON de chunks.
- Verificar individualmente las nueve secciones reportadas como omitidas: `1.8 Usos del Suelo`, `1.14 Vivienda`, `3.4.1 Usos del Suelo`, `3.6 Transporte`, `3.10 Vivienda`, `4.2 Zonificación`, `4.4 Polígonos de Actuación`, `V. Estrategia Económica` y `VI. Acciones Estratégicas`.
- Verificar individualmente las cuatro fusiones reportadas: `II. Imagen Objetivo` con `III. Estrategia de Desarrollo Urbano`; `1.24.4 Pronóstico` con encabezados posteriores; `3.14 Espacio Público` con `IV. Ordenamiento Territorial`; y `4.4 Polígonos de Actuación` con `V/VI`.
- Comprobar las líneas/fragmentos citados en el informe de Cline y registrar el identificador exacto del chunk, página PDF y encabezado fuente.
- Confirmar que los apartados realmente omitidos no estén conservados en otro artefacto o bajo una estructura diferente. No asumir que un encabezado ausente del JSON implica que el contenido está perdido sin revisar el texto completo.
- Evaluar jerarquía, continuidad, límites de chunk, contenido discontinuo, referencias cruzadas, páginas, tablas, notas y procedencia.

**M1.2 PDDU Cuauhtémoc**
- Verificar el título ya corregido contra el PDF; no volver a cambiarlo sin evidencia concreta.
- Cotejar el índice completo con los chunks actuales y documentar cada apartado ausente, incluida la discrepancia reportada entre 13 chunks y la estructura del documento.
- Confirmar los 17 cuadros identificados y sus títulos, páginas y ubicación; no usar informes con nombres de PPCU como evidencia de cuadros PDDU sin confirmar que corresponden a la fuente correcta.
- Confirmar que los Cuadros 15 y 16 son prioritarios: usos del suelo y normas de ordenación sobre vialidad.

**M1.3 Tres leyes**
- Revisar los artefactos de la Ley de Establecimientos Mercantiles, Ley de Desarrollo Urbano del DF y Ley de Cultura Cívica.
- Resolver documentalmente los desfases de versión reportados: config v2 frente a archivo v1 para Establecimientos Mercantiles; config v6.1 frente a archivo v6.4 para Desarrollo Urbano.
- Verificar configuración, fuente, fecha/versionado, chunks, embeddings, índice y cobertura por documento.
- Revisar la clasificación `tipo_disposición` y las marcas de revisión; no disminuir `needs_review` sin criterio probado y revisión humana.
- No declarar vigencia jurídica sin fuente oficial y comprobación jurídica.

**Criterio de aceptación M1:** cada discrepancia del índice y cada fusión/omisión queda cotejada contra fuente primaria, con evidencia trazable y resolución documentada o bloqueo explícito. No se regeneran artefactos hasta que la fuente y la estructura estén validadas.

#### M2. Chunks, embeddings y trazabilidad local

- Validar el esquema de chunks con el procesador productivo existente; no crear un segundo pipeline de chunking.
- Confirmar conteos por documento, jerarquía, encabezados, citas, páginas, metadatos y flags de revisión.
- Verificar correspondencia entre chunks fuente y segmentos de embeddings, considerando que un chunk puede producir varios segmentos.
- Confirmar modelo `amazon.titan-embed-text-v2:0`, dimensión 1024, identificadores, texto fuente, procedencia y asociación chunk/documento.
- Revisar duplicados, segmentos inesperados, embeddings huérfanos y diferencias entre los conteos históricos (1,235 chunks fuente y 1,369 segmentos reportados).
- Generar o regenerar chunks/embeddings únicamente después de resolver M1 y solo en local. No llamar Bedrock ni cargar Aurora en este paquete.
- Preservar artefactos existentes; no sobrescribir sin respaldo, comparación y autorización.

**Criterio de aceptación M2:** artefactos reproducibles, validación de correspondencia sin discrepancias no explicadas, conteos por documento y reporte de cualquier excepción. Los resultados deben ser verificables mediante comandos registrados.

#### M3. Inventario y estructuración de tablas/cuadros

**M3.1 PPCU**
- Inventariar y clasificar las Tablas 1–21 y 24, incluyendo título, páginas, estructura, notas, símbolos y relación con el texto.
- Tabla 22: conservar el registro existente de 357 celdas (51 actividades × 7 zonificaciones) y estados literales. Auditar procedencia y correspondencia visual.
- Mantener pendiente el significado jurídico de `permitido (*)` en el registro 29 (J-25); no inferir resolución.
- Tabla 23: no concluir que no existe hasta completar el cotejo visual exhaustivo del documento fuente.
- No convertir automáticamente tablas en embeddings ni modificar Aurora durante el inventario.

**M3.2 PDDU**
- Confirmar el inventario de 17 cuadros.
- Estructurar primero Cuadros 15 y 16, conservando `cuadro_id`, zonificaciones/celdas, estado original, páginas fuente y notas.
- No cargar ni modificar datos hasta validar el esquema y la extracción.

**Criterio de aceptación M3:** inventario completo con ubicación y estado de cada tabla/cuadro; los elementos prioritarios cuentan con representación estructurada y trazable o un bloqueo documentado.

#### M4. Cobertura del retriever e integración de recuperación estructurada

- Medir cobertura y diversidad de recuperación por cada uno de los cinco instrumentos del MVP.
- Verificar que las consultas semánticas no excluyan documentos por ranking global y registrar resultados por consulta y fuente.
- Evaluar la recuperación estructurada de Tabla 22 y definir cómo se integrarán otros cuadros/tablas sin inferir celdas ausentes.
- Revisar la integración actual en el backend/Lambda solo después de estabilizar el contrato de datos y de recuperación.
- No cambiar la estrategia de retrieval sin línea base, hipótesis, evaluación controlada y pruebas de regresión.

**Criterio de aceptación M4:** métricas y resultados por instrumento, conjunto de consultas versionado, cobertura/diversidad documentada y evidencia de que la recuperación estructurada se activa en los casos previstos.

#### M5. Pruebas reproducibles y evaluación

- Separar pruebas unitarias, offline/mock, integración local, integración AWS, E2E y evaluación jurídica humana.
- Revisar la existencia y contenido de los archivos de evaluación Semana 5; no asumir que un resultado histórico de Precision@5 representa la calidad actual.
- Fijar preguntas, fuentes/chunks esperados, criterio de relevancia, métricas (Precision@k/Recall@k cuando proceda) y rúbrica humana.
- Guardar salidas completas, IDs estables, scores, configuración, errores y anotaciones.
- Registrar cada prueba ejecutada y no afirmar aprobación sin comando y salida verificable.

**Criterio de aceptación M5:** evaluación reproducible, resultados trazables y distinción explícita entre evidencia técnica y validación jurídica.

#### M6. Arquitectura, API y experiencia de usuario

- Elaborar primero diagnóstico de arquitectura y dependencias; no reorganizar carpetas ni servicios por anticipado.
- Revisar contrato entre frontend, API, Lambda, retriever, recuperación estructurada y generador.
- Mantener pendiente la captura explícita de actividad y zonificación en frontend para consultas puntuales de Tabla 22 (S9-16).
- Revisar presentación de citas, tablas/matrices largas, estados de evidencia insuficiente y errores.
- Copilot se utilizará para frontend solo cuando el contrato de datos y recuperación esté estabilizado; Cline y Copilot no deben editar simultáneamente los mismos archivos.

**Criterio de aceptación M6:** propuesta de arquitectura respaldada por diagnóstico, contrato API documentado y pruebas de los flujos afectados antes de modificar UI/backend.

#### M7. Instructivo y replicación de AWS

- Actualizar `Instructivo_operacion.md` con la secuencia local y operativa vigente.
- Documentar identificación dinámica de recursos tras reconstrucciones Terraform, recuperación segura de Secrets Manager, túnel SSM, PGPASSFILE/PGPASSWORD, inicialización, carga y verificación.
- Diferenciar infraestructura persistente `terraform/base` de DEV efímero `terraform/dev`.
- Preparar una prueba de reconstrucción reproducible, pero no ejecutarla hasta autorización específica.
- Verificar el estado real de AWS antes de cualquier operación; no asumir que el estado histórico sigue vigente.

**Criterio de aceptación M7:** instructivo consistente con los scripts y outputs actuales, sin IDs efímeros obsoletos ni secretos.

#### M8. Seguridad, operación y cierre de DEV

- Revisar privacidad y contenido de logs, correlación de éxito/fallo, diagnóstico HTTP 500, throttling, autenticación y control de acceso.
- Revisar los pendientes S9 y S10 vinculados a logs, telemetría, errores, parámetros frontend, autenticación y presentación de matrices.
- No modificar IAM ni autenticación sin propuesta, revisión y autorización.
- Ejecutar pruebas E2E y replicación AWS únicamente con autorización específica.
- Destruir/reconstruir DEV solo al final, con aprobación explícita y comprobación de que los artefactos persistentes están respaldados; nunca afectar `terraform/base`.

**Criterio de aceptación M8:** riesgos y decisiones documentados, pruebas operativas diferenciadas, procedimiento reproducible y estado final de AWS confirmado.

### Registro del informe inicial de Cline — 25 de noviembre de 2026

Cline informó los siguientes resultados preliminares:

- PPCU: identificó las nueve omisiones y cuatro fusiones enumeradas en M1.1.
- PDDU: reportó 17 cuadros y señaló los Cuadros 15/16 como pendientes de JSON estructurado. El título del PDDU se considera ya corregido.
- Leyes: reportó chunks, embeddings e índice existentes; señaló los desfases de versión de Establecimientos Mercantiles y Desarrollo Urbano, y la alta proporción de `tipo_disposición` con `needs_review`.
- Artefactos: reportó 1,235 chunks fuente, 1,369 segmentos de embeddings y dimensión 1024.
- Tablas: reportó Tabla 22 con 357 celdas; Tablas PPCU 1–21 y 24 sin estructura normalizada; Tabla 23 no localizada.
- Pruebas: el informe afirma integridad JSON, dimensión y correspondencia chunk/embedding; sin embargo, los comandos descritos al cierre se limitan principalmente a inspección de Git/JSON. Estas afirmaciones quedan **reportadas por Cline, pendientes de reproducir y validar con comandos y salidas explícitos**.
- Cline indicó que no generó nuevos chunks ni embeddings y que no cargó Aurora ni invocó AWS/Bedrock.

**Evaluación de estado:** este informe es una inspección preliminar, no el cierre de M1 ni M2. La auditoría contra PDF, la resolución de omisiones/fusiones, la validación completa de artefactos y la aceptación de chunks/embeddings siguen pendientes. No se debe avanzar a M3 como trabajo de implementación hasta cerrar o documentar formalmente los criterios de M1 y M2.

### Siguiente paquete de trabajo

Preparar un único prompt de Cline que aborde M1.1–M1.3 y M2 en secuencia, con subpuntos numerados y reporte de evidencia por cada uno. Puede agrupar inspecciones compatibles, pero deberá detener la generación/regeneración de artefactos si encuentra una fuente no validada, una discrepancia de versión o una ambigüedad jurídica. Al finalizar, entregar matriz de estado, archivos revisados/modificados, comandos ejecutados, resultados, discrepancias, decisiones requeridas y lista exacta de puntos que habilitan M3.

### Restricciones vigentes

No se autoriza en esta entrada:
- despliegue o modificación de AWS/Terraform/IAM;
- carga, modificación o destrucción de datos Aurora;
- invocación real de Bedrock;
- modificación de retriever, API o frontend;
- reorganización de carpetas;
- commit/push de cambios de código;
- destrucción o reconstrucción de DEV.

Esta entrada registra el plan y el estado reportado. Las actividades se considerarán completadas únicamente cuando se incorporen evidencias verificables y la revisión correspondiente.
