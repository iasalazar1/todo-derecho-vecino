# Revisión editorial de auditorías PPCU — Commit 1

Fecha: 2026-11-12

Este paquete contiene versiones revisadas de tres informes documentales. Se preparó a partir de los archivos incluidos en `revision_auditorias_PPCU.tar.gz`.

## Archivos incluidos

- `auditoria_PPCU_indice.md`
- `inventario_tablas_PPCU.md`
- `leyes_cdmx/auditorias_documentales/auditoria_calidad_json_PPCU_Hipodromo.md`

## Cambios realizados

1. **Auditoría del índice:** se retiró la afirmación incorrecta de que no existía `AGENTS.md` en la raíz; se precisó qué se sabe y qué no se verificó. Se moderó la conclusión para distinguir el contenido del informe original de una nueva verificación independiente.
2. **Inventario:** se sustituyó la afirmación «Tabla 23: ausencia real» por «no localizada; existencia no determinada». Se aclaró que el salto de numeración en el texto extraído no prueba inexistencia.
3. **Auditoría de calidad:** se explicó que `cotejado` no significa necesariamente «sin discrepancias»; se señalaron las discrepancias pendientes de Tablas 7, 12, 16 y 17; se hizo explícita la falta de justificación registrada para el estado parcial de Tabla 11 e Instrumentación de Estructura Urbana.

## Límites de esta revisión

- No se modificaron los 33 JSON ni el manifiesto.
- No se modificó la auditoría específica de Tabla 22.
- No se revisó visualmente el PDF original ni se cotejaron de nuevo los valores de las tablas.
- Los conteos del manifiesto (21 cotejados, 10 parciales y 2 pendientes) se conservaron; su consistencia numérica fue comprobada contra los 33 registros incluidos en el manifiesto.
- Estas correcciones son editoriales y de control documental; no constituyen validación jurídica ni certificación de exactitud de los datos.

## Aplicación en el repositorio

Extraer este paquete desde la raíz del repositorio `todo-derecho-vecino`, conservando las rutas relativas. Antes de agregar archivos, revisar `git diff` y confirmar que solo se sustituyen los tres informes enumerados. No incluye comandos de `git add`, `commit` ni `push`.
