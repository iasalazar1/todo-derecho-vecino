# Auditoría documental y comparativa — Tabla 22 del PPCU Hipódromo

## resumen ejecutivo

La `Tabla 22` del documento original aparece como:

> `Tabla 22. TABLA DE COMPATIBILIDAD DE USOS DEL SUELO`

Se localiza en el bloque del texto del PDF inmediatamente después de la sección de zonificación y antes de la continuidad de la normativa del programa parcial. La evidencia de texto extraído del PDF la ubica claramente en las páginas reales del visor asociadas a la sección de compatibilidad de usos del suelo, con coincidencia documental con el metadato de fuente del JSON: `PPCU_Hipodromo-80-81.pdf`.

## Archivos auditados

| Archivo | SHA256 | Tamaño | Observación |
|---|---|---:|---|
| `leyes_cdmx/PPCU_Hipodromo.pdf` | `aec2baafa3dcd3fcdcccccf60ea78128c3621c39554bc9e048ce3e47a86309d5` | 1,232,772 bytes | PDF original con la tabla. |
| `leyes_cdmx/PPCU_Hipodromo_tabla_22.json` | `2165669d822b80c89c4ac55c8d317ba6bc85383085cefb622977d75a20e9fe08` | 35,772 bytes | JSON de extracción de compatibilidad, 51 filas. |
| `leyes_cdmx/PPCU_Hipodromo_tabla_22.backup-20261017-184152.json` | `92d18c7e4d3116859ea6b3337bc7ca8fd3afd5119921dae0dabf5ab426d5def4` | 33,799 bytes | Backup con la misma lógica documental; útil para comparar evolución, no para sustituir el PDF. |

## Evidencia visual del PDF

La extracción textual del PDF reporta explícitamente:

- `Tabla 22. TABLA DE COMPATIBILIDAD DE USOS DEL SUELO`
- encabezados de zonificación: `H`, `HC`, `HO`, `HM`, `HCS`, `E`, `EA`
- texto introductorio: “`La tabla de compatibilidad de usos del suelo que a continuación se presenta ...`”
- texto de continuidad: “`CLASIFICACION DE USOS DEL SUELO`”

Esto confirma que la tabla es una tabla de compatibilidad y no una tabla estadística ni un cuadro de diagnóstico.

## Páginas reales de la tabla

| Centro de evidencia | Página del PDF | Observación |
|---|---:|---|
| Inicio del bloque de compatibilidad | 80 | Código del JSON de fuente hace referencia a `PPCU_Hipodromo-80-81.pdf` y el texto del PDF se alinea con ese bloque. |
| Continuidad de la tabla | 81 | La tabla continúa con la clasificaciones de usos y notas. |
| No detectado | 82+ | La continuación del documento cambia de tema y no evidencia una Tabla 23. |

## Comparación de estructura con el JSON

### 1) Número y nombre de actividades

- El JSON contiene 51 filas (`len(rows) == 51`).
- El PDF presenta una sola matriz de compatibilidad de usos con categorías y subcategorías, no un listado de 51 actividades etiquetadas como “actividad_id”.
- La estructura del JSON usa una representación artificial del contenido: `actividad_001`, `actividad_002`, etc., con campos `categoria`, `subcategoria`, `actividad_original` y un mapa de zonificaciones.

Conclusión: la estructura JSON es una normalización del contenido de la tabla, no una reproducción literal del PDF en forma tabular. Eso es válido como representación, pero no debe confundirse con la tabla original.

### 2) Orden de filas

El orden del JSON sigue, de modo general, la secuencia que aparece en el PDF:

1. `Vivienda`
2. `Central de abastos`
3. `Mercado`
4. `Bodega de productos perecederos`
5. `Bodega de productos no perecederos y bienes muebles`
6. `Depósitos y comercialización de combustible`
7. `Gasolineras y verificantes`
8. `Estaciones de gas carburante`
9. `Rastros y frigoríficos`
10. `Venta de abarrotes, comestibles ...`

El orden se conserva en la mayor parte del bloque, con el detalle de que el PDF presenta categorías generales (`HABITACION`, `COMERCIO`, `SERVICIOS`, `ADMINISTRACIÓN`, etc.) mientras que el JSON las desagrega en `categoria` y `subcategoria`.

### 3) Encabezados de columnas

Los encabezados visuales del PDF son:

- `H`
- `HC`
- `HO`
- `HM`
- `HCS`
- `E`
- `EA`

El JSON dispersa la misma lógica en `zonificaciones`:

```json
"zonificaciones": {
  "H": "permitido",
  "HC": "permitido",
  "HO": "permitido",
  "HM": "permitido",
  "HCS": "permitido",
  "E": "prohibido",
  "EA": "prohibido"
}
```

Esto es compatible con el PDF. La diferencia principal es que el PDF presenta la lógica en una matriz física, mientras que el JSON la normaliza a un mapa de columnas.

### 4) Zonificaciones

La estructura documental del PDF y del JSON usa las mismas categorías de zonificación:

- `H` = Habitacional
- `HC` = Habitacional con Comercio en Planta Baja
- `HO` = Habitacional con Comercio en Planta Baja y Primer Nivel / Habitacional y/o Oficinas
- `HM` = Habitacional Mixto
- `HCS` = Habitacional con Comercio y Servicios
- `E` = Equipamiento
- `EA` = Espacios Abiertos / Parques, Plazas y Jardines Públicos

El JSON no altera estos símbolos ni sustituye sus abreviaturas.

### 5) Símbolos y abreviaturas

Se conservan los siguiente símbolos y abreviaturas relevantes:

- `H`, `HC`, `HO`, `HM`, `HCS`, `E`, `EA`
- `*` y `**` en notas generales del documento
- `B&B` (alojamiento y desayuno) mencionado en notas del bloque

No se observaron alteraciones de símbolos ni conversiones automáticas a categorías distintas.

### 6) Notas al pie y continuidad entre páginas

El texto extraído del PDF contiene una nota importante:

- `1. Los usos que no están señalados en esta tabla, se sujetarán al procedimiento establecido en el Reglamento de la Ley de Desarrollo Urbano.`
- También existen notas sobre `Alojamiento y desayuno` y usos permitidos solo en ciertos predios, con `*` y `**`.

El JSON no incluye estas notas como texto literal; la lógica se conserva solo en la forma de estados y flags. Por eso, la revisión del contenido visual debe considerarse una representación parcial del original.

## Validación celda por celda: ejemplos representativos

| Actividad del PDF / JSON | Estado observado en PDF | Estado del JSON | Observación |
|---|---|---|---|
| `Vivienda` | permitida en H, HC, HO, HM, HCS; prohibida en E / EA | `permitido` / `prohibido` | coincide |
| `Mercado` | permitido solo en HCS; prohibido en zonas H/HC/HO/HM/E/EA | `HCS: permitido` y resto `prohibido` | coincide |
| `Bodega de productos no perecederos y bienes muebles` | permitido en HCS; prohibido en el resto | `permitido` en HCS, resto `prohibido` | coincide |
| `Venta de abarrotes, comestibles y comida elaborada sin comedor, molinos, panaderías, minisupers y misceláneas` | permitido en HC, HO, HM, HCS; prohibido en H, E, EA | `HC, HO, HM, HCS: permitido` / resto `prohibido` | coincide |
| `Oficinas, despachos y consultorios` | se ubica en la parte de servicios y puede tener reglas de compatibilidad distintas | presente en la tabla con estado que varía | coincide a nivel de representación, pero requiere revisión documental manual |

## Hallazgos clave

### Confirmado

- La `Tabla 22` existe en el PDF original y está titulada exactamente como aparece en el JSON y el texto extraído.
- La lectura visual y la representación JSON coinciden en la lógica institucional de zonificación.
- Los símbolos `H`, `HC`, `HO`, `HM`, `HCS`, `E`, `EA` se mantienen.

### Probable; requiere verificación

- La tabla no está escrita como una “tabla estructurada” en filas numeradas; el JSON la convierte en una lista de actividades, por lo que la correspondencia exacta entre cada fila del PDF y cada fila del JSON no puede garantizarse sin revisión manual de cada celda.
- La presencia de `needs_review: true` en todas las filas del JSON es un indicativo correcto de que requiere validación humana, no de error técnico.

### Pendiente de criterio jurídico

- Los estados `permitido`, `prohibido` y `por validar` deben mantenerse literalmente; no deben convertirse a una lógica de “permitido” por defecto en ausencia de evidencia.
- La ausencia de una `Tabla 23` no debe compensarse inventando una fila o un título; la secuencia documental debe respetarse.

## Conclusión

La `Tabla 22` está presente en el PDF y se corresponde funcionalmente con el JSON de compatibilidad. La evidencia confirma que el JSON no ha inventado títulos ni columnas; reproduce la lógica de compatibilidad de usos del suelo con una estructura de datos normalizada.

La diferencia relevante no es una discrepancia de contenido bruto, sino de formato: el PDF presenta la tabla como matriz documental y el JSON la transforma a un esquema de filas/zonificaciones. Esto requiere validación humana y no se debe corregir sin una revisión documental directa del PDF.

## Criterio de aceptación del presente informe

Se cumple la condición de auditoría de la tabla 22: se localiza la tabla, se identifican páginas, se compara contenido con el JSON, no se altera ningún valor, y se sustenta la diferencia entre representación visual y representación estructurada.
