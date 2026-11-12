# Diseño del modelo de datos estructurados del PPCU Hipódromo

## 1. Propósito y límites

Proponer una organización documental y de datos para las tablas y cuadros del Programa Parcial de Desarrollo Urbano de la colonia Hipódromo (PPCU), separando los datos originales de su normalización y de cualquier interpretación. El diseño busca que la futura aplicación pueda consultar tanto texto mediante pgvector como datos tabulares mediante SQL, conservando procedencia y estado de revisión.

Este documento es una propuesta, no una especificación ya aprobada para producción. No se modificaron los JSON, el PDF, los chunks, el código, el esquema SQL ni AWS. La Tabla 22 existente se trata como inmutable mientras el usuario revisa sus registros `por validar`.

## 2. Fuentes inspeccionadas y alcance de evidencia

Fuentes locales consultadas:

- `leyes_cdmx/PPCU_Hipodromo.pdf` — original, 122 páginas.
- `leyes_cdmx/PPCU_Hipodromo_extracted.txt`
- `leyes_cdmx/PPCU_Hipodromo_reviewed.txt`
- `leyes_cdmx/PPCU_Hipodromo_reviewed_chunks.json` — 52 chunks.
- `leyes_cdmx/PPCU_Hipodromo_tabla_22.json` — 51 registros de actividades.
- `inventario_tablas_PPCU.md`, `auditoria_PPCU_indice.md` y `auditoria_PPCU_tabla_22.md`.

Los números de página indicados abajo son páginas físicas del PDF según extracción con número de página; no son necesariamente la numeración impresa. Se revisó visualmente el intervalo PDF 82–89 para explorar el salto entre las Tablas 22 y 24. No se realizó una inspección visual completa de las 122 páginas. Por ello, “no localizado” no significa “inexistente” si no se ha verificado el documento completo.

## 3. Inventario funcional y estado de estructuración

El inventario siguiente conserva la numeración y los títulos detectados, sin renumerar. Las páginas identifican dónde la extracción localiza el rótulo; continuidad final y contenido interno deben confirmarse visualmente antes de ingerirlos. Las tablas 1–21 y 24 están identificadas en el PDF/textos, pero no se encontraron archivos JSON de datos independientes para ellas.

| N.º original | Título registrado en la fuente derivada | Página PDF con rótulo | Clase funcional propuesta | Estado |
|---|---|---:|---|---|
| 1 | Mezcla de usos del suelo en el Distrito I | 21 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 2 | Mezcla de usos del suelo en el Distrito II | 21 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 3 | Mezcla de usos del suelo en el Distrito III | 22 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 4 | Mezcla de usos del suelo en el Distrito IV | 22 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 5 | Mezcla de usos del suelo en el Distrito V | 23 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 6 | Mezcla de usos del suelo en el Distrito VI | 23 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 7 | Oferta y demanda por Distritos | 29 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 8 | Equipamiento. Subsistema Salud | 35 | Estadística y diagnóstico de equipamiento | Identificada; sin JSON propio |
| 9 | Equipamiento. Subsistema Educación | 36–37 | Estadística y diagnóstico de equipamiento | Identificada; continuación expresamente rotulada |
| 10 | Equipamiento. Subsistema Servicios Urbanos | 39 | Estadística y diagnóstico de equipamiento | Identificada; sin JSON propio |
| 11 | Equipamiento. Subsistema Administración Pública | 40 | Estadística y diagnóstico de equipamiento | Identificada; sin JSON propio |
| 12 | Tendencia decreciente de la población | 41 | Estadística y diagnóstico demográfico | Identificada; sin JSON propio |
| 13 | Tabla comparativa de ocupación por vivienda | 42 | Estadística y diagnóstico de vivienda | Identificada; sin JSON propio |
| 14 | Tipo de vivienda | 42 | Estadística y diagnóstico de vivienda | Identificada; sin JSON propio |
| 15 | Materiales utilizados en la construcción de vivienda | 42 | Estadística y diagnóstico de vivienda | Identificada; sin JSON propio |
| 16 | Número de cuartos en la vivienda | 42 | Estadística y diagnóstico de vivienda | Identificada; sin JSON propio |
| 17 | Tenencia | 43 | Estadística y diagnóstico de vivienda | Identificada; sin JSON propio |
| 18 | Vacantes urbanas | 44 | Estadística y diagnóstico territorial | Identificada; sin JSON propio |
| 19 | Uso predominante del suelo en edificios catalogados | 45 | Diagnóstico territorial y patrimonial | Identificada; sin JSON propio |
| 20 | Normatividad por vialidad | 60–61 | Normativa y ordenamiento territorial | Identificada; continuación expresamente rotulada |
| 21 | Tendencias programáticas de población Programa de Desarrollo Urbano Delegacional | 66 | Estadística / programación demográfica | Identificada; sin JSON propio |
| 22 | TABLA DE COMPATIBILIDAD DE USOS DEL SUELO | 80; fuente derivada refiere 80–81 | Compatibilidad de usos de suelo | JSON existente; la carga histórica de 357 celdas está documentada en Bitácora; estado actual de Aurora no verificado |
| 23 | No localizada | — | No clasificable todavía | No aparece en la extracción consultada; falta revisar visualmente el PDF completo |
| 24 | Tipo de intervencion segun niveles de protección | 89 | Protección y restricciones | Identificada; sin JSON propio |
| — | TABLA DE PROGRAMA DE ACCIONES PRIORITARIAS | 101 | Acciones estratégicas y programación | Tabla identificada sin número explícito |

Elementos que no deben confundirse con tablas:

| Elemento | Página PDF detectada | Clasificación | Estado |
|---|---:|---|---|
| Mapa Mental | 49 | Ejercicio gráfico de consulta participativa | Referencia detectada; elemento y alcance visual pendientes de inventario completo |
| Gráfica 24. Población residente y flotante en día hábil (imagen objetivo) | 72 | Gráfica | Referencia detectada; no es una tabla |

Los textos también aluden a otras gráficas y planos, pero este inventario no pretende afirmar que la lista gráfica esté completa. La comprobación de cada página y elemento gráfico es una tarea de auditoría documental separada.

### Situación de Tabla 23

La extracción textual no contiene un rótulo `Tabla 23`; el rótulo siguiente reconocido es `Tabla 24` en la página PDF 89. Las páginas PDF 82–89 revisadas visualmente no muestran una Tabla 23. Como no se inspeccionaron visualmente todas las páginas del documento, el catálogo debe registrar la Tabla 23 como `no localizada; inspección visual completa pendiente`, no crear un archivo con un título supuesto ni afirmar su ausencia definitiva.

## 4. Clasificación y requisitos de datos

### Estadísticas y diagnóstico

Aplicable, sujeto a verificación visual, a Tablas 1–19 y 21.

- Conservar literalmente encabezados, rótulos, unidades, categorías, totales, porcentajes y períodos.
- Registrar cada celda como valor original, sin recalcular porcentajes ni convertir descripciones en conclusiones.
- Para consultas numéricas, conservar tanto la cadena original como, si se valida, un valor tipado independiente y la unidad explícita.
- Advertir cuando el período, denominador, unidad o método no estén expresados en la fuente.

### Normativa y ordenamiento territorial

Aplicable a Tabla 20 y a normas tabuladas que se confirmen en el documento.

- Conservar vialidad/distrito, clasificación normativa, medida/unidad, condición, excepción y texto literal.
- Representar una condición o excepción en campos separados solo cuando la fuente la exprese; conservar además la fila original para no perder contexto.
- No inferir el alcance territorial ni que la norma siga vigente.

### Compatibilidad de usos de suelo

Aplicable a Tabla 22.

- Conservar actividad y categoría en el orden de la tabla, símbolos de zonificación y el estado literal de cada celda.
- Una celda es la unidad recuperable para preguntas por actividad y zonificación; las siete celdas de una actividad deben poder vincularse a una misma fila documental.
- Mantener `permitido`, `prohibido` y `por validar` tal como estén en la fuente de datos; mantener `needs_review: true` mientras así esté marcado.
- El JSON actual representa una actividad por objeto con un mapa de siete zonas; el cargador lo transforma en filas actividad-zonificación. La propuesta no cambia ninguno de esos datos.

### Protección y restricciones

Aplicable a Tabla 24 y a cualquier otro elemento que, tras revisión, exprese restricciones por nivel, tipo de intervención, elemento o condición.

- Conservar el rótulo original de cada nivel y la expresión literal de cada celda, incluyendo “permitida”, “prohibida”, “condicionada” o “restringida” cuando esos términos efectivamente aparezcan.
- Separar condición original de cualquier clasificación analítica añadida posteriormente.
- Vincular cada celda con título, número, página, fila, columna y notas aplicables.

### Acciones estratégicas y programación

Aplicable a `TABLA DE PROGRAMA DE ACCIONES PRIORITARIAS`, sin número identificado.

- Conservar eje, programa, acción, institución/plazo/metas solo si aparecen en la tabla.
- No inventar número de tabla, responsables, fechas ni indicadores ausentes.
- Marcar el identificador como no numerado en el documento y mantener el título literal.

## 5. Arquitectura JSON propuesta

### Archivos por tabla

Se propone un JSON independiente por cada tabla cuya existencia, título y contenido hayan sido confirmados visualmente; por ejemplo, `PPCU_Hipodromo_tabla_01.json`, `PPCU_Hipodromo_tabla_20.json`, `PPCU_Hipodromo_tabla_22.json` y `PPCU_Hipodromo_tabla_24.json`. La convención es ilustrativa: no autoriza crear datos para tablas no auditadas. La tabla de acciones sin número requiere una denominación que no invente numeración y deberá acordarse cuando se confirme su estructura.

`PPCU_Hipodromo_tabla_22.json` ya existe y está excluido de la modificación. No se generará una versión alternativa ni se presentará aquí un JSON sustitutivo.

### Envolvente común propuesta

Todos los JSON futuros compartirían metadatos de documento, tabla, fuente y revisión, y un arreglo `registros`. Los campos comunes no fuerzan una misma forma para los datos:

```json
{
  "schema_version": "propuesta-1",
  "documento": {
    "documento_id": "ppdu_hipodromo",
    "titulo_documental": "Programa Parcial de Desarrollo Urbano Hipódromo",
    "archivo_pdf": "leyes_cdmx/PPCU_Hipodromo.pdf",
    "sha256_pdf": "pendiente_de_registrar_en_ingesta"
  },
  "tabla": {
    "tabla_id": "tabla_N",
    "numero_original": "N",
    "titulo_literal": "transcripción verificada del rótulo",
    "tipo_funcional": "clasificación documental no jurídica",
    "paginas_pdf": [],
    "estado_extraccion": "pendiente_revision_visual"
  },
  "revision": {
    "needs_review": true,
    "estado_revision": "pendiente",
    "observaciones_auditoria": []
  },
  "registros": []
}
```

Los valores de ejemplo `N`, páginas, hash y título son marcadores, no datos del PPCU. No deben escribirse como contenido real. Para elementos no numerados, `numero_original` debe indicar explícitamente `null` y el catálogo debe mantener la condición `sin_numero`, no asignarles un número.

Cada registro debe incluir, según corresponda:

- `registro_id` estable dentro del archivo y `orden_original`.
- `pagina_pdf` (y página impresa solo si se verifica).
- `fila_original`, `columna_original` o coordenadas equivalentes cuando existan.
- `texto_original` y `valores_originales`.
- `notas_referidas` y texto literal de notas disponible.
- `datos_estructurados`, con esquema dependiente del tipo de tabla.
- `interpretaciones`, vacío salvo clasificación explícitamente documentada y separada del original.
- `needs_review`, `estado_revision` y `observaciones_auditoria`.

### Campos específicos sugeridos

| Tipo funcional | `datos_estructurados` puede incluir | Precaución |
|---|---|---|
| Estadística/diagnóstico | indicador, categoría territorial, valor_original, unidad_original, período_original, denominador_original | No computar valores derivados sin conservar el cálculo y aprobación |
| Normativa/vialidad | distrito, vialidad_original, parámetro_original, unidad_original, condición_original, excepción_original | No inferir aplicabilidad fuera del texto |
| Compatibilidad | actividad, código_zonificación, estado_original | La Tabla 22 existente no se cambia; preservar sus estados y marcas |
| Protección/restricción | nivel_original, intervención_original, condición_original | No sustituir términos fuente por una interpretación |
| Programación/acciones | eje_original, acción_original, actor_original, plazo_original, meta_original | Registrar solo campos presentes |

## 6. Catálogo maestro propuesto

Nombre propuesto: `PPCU_Hipodromo_catalogo_tablas.json`.

Debe ser un índice pequeño, no una copia de filas, celdas o notas. Cada entrada puede tener: identificador original, título literal, número o estado sin número, tipo funcional, ruta al JSON correspondiente (si existe), páginas del PDF, SHA-256 del PDF de origen, estado de identificación/extracción, bandera de revisión y referencia al informe de auditoría.

Estados de catálogo propuestos:

- `confirmada_en_fuente`: existencia y rótulo cotejados con el PDF.
- `identificada_extraccion_pendiente_visual`: rótulo localizado, tabla aún no contrastada visualmente en su totalidad.
- `json_existente_pendiente_revision`: archivo JSON presente y no autorizado para alteración.
- `no_localizada_inspeccion_pendiente`: no aparece en los textos revisados y falta revisión visual completa.
- `no_es_tabla`: figura, mapa, gráfica u otro elemento clasificado por separado.

Ejemplos de estados según la evidencia actual:

- Tabla 22: JSON existente; metadatos/celdas requieren cotejo manual. No cambiar.
- Tablas 1–21 y 24: rótulos detectados; JSON por tabla no localizado; detalle requiere cotejo visual.
- Tabla 23: no localizada en texto; no ausencia definitiva.
- Tabla de acciones prioritarias: identificada sin número; normalización pendiente.

## 7. Separación de original, normalización e interpretación

1. **Original:** transcripción de encabezados, celdas, texto, símbolos y notas con página y posición.
2. **Normalización:** campos tipados que permiten buscar/filtrar (por ejemplo, valor numérico o zonificación); deben apuntar al valor original.
3. **Clasificación:** categoría funcional de la tabla y tipo de dato, claramente marcada como metadato de organización.
4. **Interpretación jurídica:** no se genera en la ingestión. Requiere revisión competente y se mantiene aparte de la evidencia literal.

Un estado de compatibilidad no se deduce de un símbolo dudoso, una celda en blanco, una nota ambigua o una extracción OCR incompleta. En esos casos se conserva la fuente disponible y el pendiente de revisión; no se completa por inferencia.

## 8. Decisiones para una futura fase

- Validar visualmente todas las tablas y elementos gráficos, incluyendo páginas finales y continuidad.
- Definir si se almacenan imágenes/crops de tablas como artefactos de auditoría y dónde.
- Aprobar el esquema común y los esquemas específicos antes de generar JSON por tabla.
- Resolver la discrepancia observada en procedencia de Tabla 22: los registros JSON indican página `[80]`, mientras el nombre del archivo citado refiere `80-81`; no modificar el archivo hasta que el usuario termine la limpieza manual.
- Acordar política de versionado del catálogo y los JSON, y cómo se conserva cada hash de fuente.

La alternativa de almacenamiento y su relación con el retriever se documentan en [propuesta_esquema_postgresql_PPCU.md](./propuesta_esquema_postgresql_PPCU.md) y [diseno_retriever_hibrido_PPCU.md](./diseno_retriever_hibrido_PPCU.md).
