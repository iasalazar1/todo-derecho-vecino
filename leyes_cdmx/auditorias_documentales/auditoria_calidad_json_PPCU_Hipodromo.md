# Auditoría de calidad de los JSON tabulares del PPCU Hipódromo

**Fecha de auditoría:** 2026-11-12
**Rama:** `mvp-estancia`
**Fuente principal:** [PPCU_Hipodromo.pdf](../PPCU_Hipodromo.pdf), 122 páginas físicas.
**SHA-256 de la fuente:** `aec2baafa3dcd3fcdcccccf60ea78128c3621c39554bc9e048ce3e47a86309d5`

## Alcance y método

Se revisaron los 33 JSON enumerados en [manifiesto_procesamiento_PPCU_Hipodromo.json](../tablas_estructuradas/manifiesto_procesamiento_PPCU_Hipodromo.json) y se contrastaron con las páginas físicas indicadas en cada archivo. El alcance del cotejo varía según el elemento: 21 están clasificados como cotejados, 10 como parciales y 2 como pendientes. El cotejo combinó lectura visual de las páginas y extracción de texto como apoyo; la extracción no se trató como sustituto de la fuente visual.

El alcance comprende las Tablas 1–21 y 24, la tabla de Acciones Prioritarias, nueve tablas de Instrumentación y la matriz de catalogación. Las referencias de página de este informe son páginas físicas del PDF, no numeración impresa.

No se interpretó jurídicamente el contenido ni se armonizaron discrepancias de la fuente. Se conservaron `needs_review: true` y los valores literales dudosos. La Tabla 22, la Tabla 23, las gráficas, los chunks, los embeddings, el código, SQL y la infraestructura no forman parte de las correcciones.

## Criterio de lectura de los estados de cotejo

Los estados `cotejado`, `parcial` y `pendiente` describen el alcance del cotejo documental registrado en el manifiesto; no expresan vigencia ni validación jurídica. En particular, `cotejado` no debe interpretarse automáticamente como ausencia de discrepancias o como confirmación de todos los valores: un elemento puede haber sido revisado contra la página fuente y conservar una discrepancia puntual sin resolver.

Esta distinción es relevante para las Tablas 7, 12, 16 y 17: el manifiesto las clasifica como `cotejado`, pero también registra discrepancias pendientes. En la Tabla 7 persisten dos diferencias: `+6` en la fuente frente a `+46` en la transcripción revisada para Distrito IV, y la separación ambigua de `-303 6` para Distrito V; en la Tabla 12 se conserva la diferencia `12,442` / `12,742`; en la Tabla 16 se mantiene como observación el punto separado debajo de la nota; y en la Tabla 17 coexisten las referencias al XI y al IX Censo. Estos casos no deben presentarse como discrepancias resueltas.

También hay dos registros clasificados como `parcial` cuya justificación no está desarrollada en los campos `incidencias` ni `discrepancias_pendientes` del manifiesto: **Tabla 11** e **Instrumentación de Estructura Urbana**. El estado se conserva tal como está, pero su motivo requiere documentación adicional antes de considerar completo el control de calidad. Esta revisión no modifica el manifiesto ni reasigna estados.

## Correcciones documentales confirmadas

| Elemento | Página física | Hallazgo en el JSON | Corrección aplicada |
|---|---:|---|---|
| Tablas 1–6 | 21–23 | Las columnas indicaban `M²`, aunque el encabezado impreso dice `M2`; tampoco se conservaban los encabezados agrupados. | Se ajustó la unidad literal a `M2` y se registraron los grupos `Planta Baja` y `Plantas Altas`. Los valores de las celdas no cambiaron. |
| Tabla 8 | 35 | El domicilio del Hospital Lourdes tenía acento en “Álvaro”, ausente en la impresión. | Se conservó `Alvaro Obregón #101`. La dirección `Sinaloa s/Nuevo` sigue dudosa y no se reinterpretó. |
| Tabla 9 | 36–37 | Cámara de Comercio y Amado Nervo estaban fusionados; había errores en `Choapan`, `Insituto Avignon` y `Bajío #307`; se repetían rótulos en celdas visualmente combinadas. | Se separaron las dos instituciones, quedando 48 filas; se corrigieron las transcripciones literales y se documentaron los rangos de celdas combinadas. El cotejo individual de todas las direcciones sigue parcial. |
| Tabla 10 | 39 | `Gasolinera` estaba repetido en seis celdas que aparecen vacías en la columna Elemento. | Se conservaron vacías las seis celdas y se verificaron visualmente las siete filas. |
| Tabla 12 | 41 | La celda de 1995 para Vivienda/Delegación decía `150,100`; la impresión dice `150100`. Faltaba la jerarquía de encabezados. | Se restauró `150100` y se registraron los grupos Población y Vivienda. |
| Tabla 13 | 42 | Las cuatro unidades omitían el espacio impreso en `hab. /vivienda`; la nota cambiaba `vivienda` a mayúscula. | Se preservaron el espaciado y la capitalización de la fuente. |
| Tabla 15 | 42 | Se habían rellenado tres celdas vacías de Elementos; la nota cambiaba capitalización y puntuación. | Se vaciaron esas celdas y se restauró la nota literal. |
| Tabla 16 | 42 | El título omitía el punto final; la nota alteraba la capitalización de `vivienda`. | Se restauró el título y la nota. El punto que aparece separado debajo de la nota se conserva como observación visual no resuelta; no se atribuye a la nota ni se incorpora silenciosamente al texto. |
| Tabla 17 | 43 | `Categoría`, `Cantidad` y `Porcentaje` aparecían como encabezados, pero no están impresos. | Se retiraron esos rótulos inferidos y se conservaron tres columnas sin encabezado. |
| Tabla 18 | 44 | No se representaba la jerarquía `Vacantes Urbanas` → `Baldíos` / `Estacionamientos` / `Total`. | Se añadieron los encabezados agrupados. No se modificaron los valores. |
| Tabla 19 | 45 | Se omitía el encabezado combinado `Edificios catalogados`. | Se documentó el grupo que abarca `Núm.` y `%`. |
| Tabla 21 | 66 | Se omitían `Datos historicos` y `Datos programaticos`. | Se incorporaron ambos grupos con sus subencabezados literales. |
| Tabla 24 | 89 | Los encabezados Nivel 1–3 estaban fusionados con sus descripciones, con dos puntos que no aparecen en la fuente. | Se separaron los encabezados principales y secundarios. Se conservaron las celdas combinadas de datos cotejadas visualmente. |

## Discrepancias de la fuente conservadas

- **Tabla 7, página 29:** la fuente muestra `+6` para Distrito IV, frente a `+46` en la transcripción revisada. Para Distrito V se conserva literalmente `-303 6`, incluida la separación visible; no se recalculó ni se decidió si representa un único número.
- **Tabla 12, página 41 y Tabla 21, página 66:** la Tabla 12 muestra `12,442`, mientras que el texto de la página y la Tabla 21 muestran `12,742`. Ambas apariciones se conservaron sin armonización.
- **Tabla 17, página 43:** el texto introductorio menciona el XI Censo y la nota de la tabla menciona el IX Censo. Se mantienen ambas referencias.
- **Tabla 8, página 35:** `Sinaloa s/Nuevo` no se pudo leer con certeza.
- **Instrumentación Físico Natural, página 112:** hay un fragmento de instrumentación sin subprograma legible; no se atribuyó a ninguna fila.

Estas observaciones describen la fuente y no constituyen una resolución jurídica o estadística.

## Elementos que permanecen parciales o pendientes

El manifiesto registra **21 cotejados, 10 parciales y 2 pendientes**:

- **Parciales (10):** Tablas 8, 9 y 11; Instrumentación Físico Natural, Equipamiento, Vialidad y Transporte, Imagen Urbana y Espacio Público, Sitios Patrimoniales, Estructura Urbana e Infraestructura. Persisten direcciones, celdas extensas, continuaciones o atribuciones que requieren cotejo ampliado. Para **Tabla 11** e **Instrumentación de Estructura Urbana**, el manifiesto no registra una incidencia ni una discrepancia que explique el estado parcial; esa justificación debe documentarse.
- **Pendientes (2):**
  - **Tabla de Acciones Prioritarias**, páginas 101–104: se distinguen cuatro páginas y 11 columnas, pero el orden de lectura mezcla celdas y no permite atribuir todas las filas con seguridad.
  - **Matriz de niveles de intervención por calidad de catalogación**, página 119: la lámina escaneada permite reconocer el título y parte de la estructura, pero no leer las celdas con confianza.
- **Tabla 23:** permanece `no_localizada`; esta auditoría no afirma que no exista. La falta de referencia en el texto extraído no equivale a una comprobación exhaustiva de inexistencia en el PDF.

Los estados de cotejo son documentales. No expresan vigencia ni validación jurídica.

## Validación e integridad

- Los **33 JSON** del manifiesto se analizaron sintácticamente; todos son JSON válido y conservan `needs_review: true`.
- La Tabla 9 tiene 48 filas estructuradas de cinco columnas; sus rangos de celdas combinadas están documentados.
- Los cambios se limitaron a los JSON en alcance y al manifiesto. No se modificaron archivos de código, infraestructura, SQL, chunks, embeddings ni documentos de control.
- La Tabla 22 y su respaldo no se editaron como parte de esta auditoría. Durante el trabajo se detectó que el SHA-256 de `PPCU_Hipodromo_tabla_22.json` difería de la instantánea de integridad inicial; la usuaria confirmó que era un cambio propio. Se preservó el archivo y no se examinó su contenido. El resto de los archivos excluidos comparados con la instantánea conserva sus hashes.
- No se hizo commit ni push.

## Archivos de auditoría y datos actualizados

- [Manifiesto de procesamiento y auditoría](../tablas_estructuradas/manifiesto_procesamiento_PPCU_Hipodromo.json)
- JSON corregidos: Tablas 1–6, 8–13, 15–19, 21 y 24, bajo [tablas_estructuradas](../tablas_estructuradas).
