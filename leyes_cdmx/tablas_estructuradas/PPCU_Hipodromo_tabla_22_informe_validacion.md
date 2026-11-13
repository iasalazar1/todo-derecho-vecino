# Informe de validación — Normalización de Tabla 22 del PPCU Hipódromo

## Alcance

Normalización estructural y organización de archivos de la Tabla 22 únicamente. Se utilizó el JSON fuente existente; no se repitió el cotejo del PDF. No se realizaron cambios de código, SQL, infraestructura, Aurora, embeddings ni en AWS.

## Rama y entradas revisadas

- Rama: `mvp-estancia`.
- Fuente estructurada: `leyes_cdmx/PPCU_Hipodromo_tabla_22.json`.
- Convenciones tabulares revisadas: `leyes_cdmx/tablas_estructuradas/PPCU_Hipodromo_tabla_01.json`, `PPCU_Hipodromo_tabla_20.json` y `PPCU_Hipodromo_matriz_intervencion_catalogacion.json`.
- Título literal contrastado con material de auditoría ya existente: `auditoria_PPCU_tabla_22.md` e `inventario_tablas_PPCU.md`.

## Archivos creados

1. `PPCU_Hipodromo_tabla_22.json` — matriz normalizada.
2. `PPCU_Hipodromo_tabla_22_notas.json` — catálogo independiente de notas.
3. `PPCU_Hipodromo_tabla_22_informe_validacion.md` — este informe.

## Estructura resultante

- **Matriz:** metadatos de tabla (`identificador`, `titulo_literal`, `tipo_elemento`, `documento_id`, documento fuente, páginas, columnas y zonificaciones), `actividades` con los datos originales de cada registro, `referencias_notas` por clave de zonificación/celda, conteos, observaciones, estado de cotejo y `needs_review`.
- **Catálogo:** metadatos de procedencia y cinco objetos de nota con `nota_id`, `marcador`, `tipo`, `alcance`, `texto_literal`, `fuente` y `needs_review`.
- El título literal utilizado es `TABLA DE COMPATIBILIDAD DE USOS DEL SUELO`, conforme al material de auditoría e inventario ya existente; se mantiene separado del identificador `tabla_22`.

## Validaciones

| Comprobación | Resultado |
|---|---|
| JSON fuente y salidas parseables | Aprobada |
| Actividades / identificadores únicos | 78 / 78 |
| Zonificaciones por actividad | 7: H, HC, HO, HM, HCS, E y EA |
| Celdas de compatibilidad | 546 |
| Categorías, subcategorías, nombres, alias, IDs, estados y procedencia por actividad | Igualdad exacta contra fuente |
| `needs_review` en tabla, actividades y catálogo | Todos `true` |
| Marcadores en celdas | `permitido (*)`: 13; `permitido (**)`: 2 |
| Notas en catálogo | 5; textos literales conforme a la solicitud |
| Referencias a `nota_asterisco_1` / `nota_asterisco_2` | 13 / 2 |
| Referencias a doble asterisco en `actividad_029` | 0 |
| Referencias adicionales no autorizadas | 0 |
| Notas generales 1 y 2; nota 3 contextual sin vínculo automático | Aprobado |
| Archivo fuente original | Conservado sin modificación |

## Diferencias respecto de la fuente

1. **Campos agregados:** metadatos a nivel de tabla conforme a las convenciones de `tablas_estructuradas`; `tipo_elemento`, columnas, zonificaciones, conteos y estado de cotejo; referencias de notas por celda; catálogo independiente con procedencia.
2. **Organización:** la lista original de registros ahora aparece como `actividades` dentro de un objeto de tabla. Cada actividad conserva los campos originales, incluido `fuente` y su página. `documento_id` y `tabla_id`, comunes a los registros, quedan en los metadatos de tabla.
3. **Relaciones:** solo se incorporaron las 15 relaciones solicitadas a las celdas correspondientes; ninguna otra celda recibe una nota.
4. **Datos preservados:** 78 identificadores; categorías, subcategorías, nombres originales, alias, siete estados por actividad, valores con marcadores, procedencia por registro y `needs_review=true`. La comparación se hizo campo a campo y por cada zonificación, no mediante comparación textual global.

## Estado de Git y límites

- Los tres archivos de salida se crearon bajo `leyes_cdmx/tablas_estructuradas/`.
- El JSON fuente no fue modificado.
- Se dejaron intactos los cambios locales preexistentes en `ajustes_pendientes.md`, `terraform/dev/api_gateway.tf` y los elementos sin seguimiento `.kilo/`, `_PPCU.md` y `lh auditoria_PPCU_indice.md auditoria_PPCU_tabla_22.md inventario_tablas_PPCU.md`.
- No se ejecutó commit ni push.
- La revisión global previa reportó un espacio en blanco final preexistente en `ajustes_pendientes.md`; no se alteró ese archivo para corregirlo.
- No se ejecutaron comandos ni operaciones en AWS.
