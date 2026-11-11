# Auditoría documental del índice — PPCU Hipódromo

## Alcance y método

Este informe compara el índice del documento original con los archivos derivados para verificar si la estructura administrativa y normativa del PPCU está representada sin alterar su jerarquía, numeración ni ubicación.

No se modificaron archivos originales. La auditoría se basa en:

- PDF original: `leyes_cdmx/PPCU_Hipodromo.pdf`
- Texto extraído: `leyes_cdmx/PPCU_Hipodromo_extracted.txt`
- Texto revisado: `leyes_cdmx/PPCU_Hipodromo_reviewed.txt`
- JSON de chunks: `leyes_cdmx/PPCU_Hipodromo_reviewed_chunks.json`

## Estado documental general

| Archivo | SHA256 | Tamaño | Páginas / filas | Rama / versión | Observación |
|---|---|---:|---:|---|---|
| `leyes_cdmx/PPCU_Hipodromo.pdf` | `aec2baafa3dcd3fcdcccccf60ea78128c3621c39554bc9e048ce3e47a86309d5` | 1,232,772 bytes | 122 páginas | `mvp-estancia` | Documento base original; fecha de modificación disponible en metadatos del PDF (`2001-10-02`). |
| `leyes_cdmx/PPCU_Hipodromo_extracted.txt` | `25636a080051321a8e686939d34187ee2c350ce9948f992efbe1d915d058390d` | 373,389 bytes | texto completo | `mvp-estancia` | Extracción primaria; conserva el índice y la numeración general. |
| `leyes_cdmx/PPCU_Hipodromo_reviewed.txt` | `49770bd6c72bc7785d7e89bdf9c017a96358741adc4ac79f18ca2f4590ea61fd` | 277,021 bytes | texto revisado | `mvp-estancia` | Revisión visual del OCR; presenta el índice y los bloques de contenido con duplicados y saltos. |
| `leyes_cdmx/PPCU_Hipodromo_reviewed_chunks.json` | `e61ecd2835a49504843869e69e3a21e18e4e9fa7041cfc8d2d3f107f1c36c8c3` | 316,017 bytes | 52 chunks | `mvp-estancia` | Representa la estructura del documento como secciones/chunks y revela omisiones. |

## Observaciones de contexto

- No existe `AGENTS.md` en la raíz ni en `Contexto/`. La lectura obligatoria del archivo guía no fue posible por ausencia del mismo.
- Sí está disponible `ajustes_pendientes.md` y el contenido de la rama confirma la advertencia sobre índices duplicados y numeración sospechosa.
- La bitácora del proyecto (`Bitacora.md`) menciona explícitamente el problema de “bloques de índice duplicados” y que el PPCU “aparece repetido en al menos tres pasadas distintas” dentro del mismo documento.
- El PDF original conserva el índice real en su página inicial y en el cuerpo del texto. La revisión de la estructura confirma que la duplicación es documental: el índice se repite como bloque antes del cuerpo y la extracción automática lo reproduce como encabezados independientes.

## Matriz de validación del índice

| Número | Título original | Página impresa | Página PDF | Texto extraído | Texto revisado | JSON | Observaciones |
|---|---|---|---|---|---|---|---|
| 0 | `I N D I C E` | 1-2 | 1-2 | Confirmado | Confirmado | No | El índice aparece al inicio del documento; se sospecha que se repite como encabezado “ÍNDICE” dentro del texto principal. |
| I | `FUNDAMENTACIÓN, MOTIVACIÓN Y DIAGNÓSTICO` | índice | 1-2 / cuerpo | Confirmado | Confirmado | Confirmado parcialmente | Se representa en chunks, pero el bloque de índice se mezcla con el texto principal y algunos títulos no se registran como secciones separadas. |
| 1.1 | `Fundamentación Jurídica` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Aparece como chunk real y como encabezado del texto. |
| 1.2 | `Definición del Área de Estudio` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra correctamente en chunks. |
| 1.3 | `Antecedentes Históricos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra correctamente. |
| 1.4 | `Ámbito Urbano y/o Metropolitano` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra correctamente. |
| 1.5 | `Medio Natural` | índice | cuerpo | Confirmado | Confirmado | Repetido / incompleto | El documento presenta `1.5.1` y `1.5.2`; el chunk no conserva una sección `1.5` explícita, aunque el desarrollo sí existe. |
| 1.5.1 | `Elementos del Medio Natural` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Sector estructural válido. |
| 1.5.2 | `Problemática Ambiental` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Sector estructural válido. |
| 1.6 | `Análisis Demográfico y Socioeconómico` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra en chunks. |
| 1.6.1 | `Aspectos Demográficos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra en chunks. |
| 1.6.2 | `Aspectos Económicos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra en chunks. |
| 1.6.3 | `Aspectos Sociales` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra en chunks. |
| 1.7 | `Estructura Urbana` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra en chunks. |
| 1.8 | `Usos del Suelo` | índice | cuerpo | Confirmado | Confirmado | Omitido | El PDF indica este título en el índice, pero el chunk JSON salta de `1.7` a `1.9`; faltante real. |
| 1.9 | `Estructura Vial` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Aparece en chunks y texto. |
| 1.10 | `Transporte Público` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.11 | `Estacionamientos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.12 | `Infraestructura` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.13 | `Equipamiento y Servicios` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.14 | `Vivienda` | índice | cuerpo | Confirmado | Confirmado | Omitido | El chunk JSON presenta `1.13`, luego `1.15`; falta la sección 1.14. |
| 1.15 | `Asentamientos Irregulares` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.16 | `Tenencia de la Tierra` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.17 | `Reserva Territorial y Baldíos Urbanos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.18 | `Sitios Patrimoniales` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.19 | `Fisonomía Urbana` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.20 | `Espacio Público` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.21 | `Riesgos y Vulnerabilidad` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.22 | `Evaluación del Programa Delegacional 1997` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se comporta bien. |
| 1.22.1 | `Normatividad` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se comporta bien. |
| 1.22.2 | `Operatividad` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se comporta bien. |
| 1.23 | `Otras Disposiciones ...` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.24 | `Síntesis de la Situación Actual` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.24.1 | `Aspectos Ambientales` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.24.2 | `Aspectos Socioeconómicos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.24.3 | `Aspectos Urbanos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 1.24.4 | `Pronóstico` | índice | cuerpo | Confirmado | Confirmado | Unido a otro bloque | El chunk JSON lo fusiona con “II. IMAGEN OBJETIVO III. ESTRATEGIA DE DESARROLLO URBANO”, lo que evidencia un problema de segmentación. |
| II | `IMAGEN OBJETIVO` | índice | cuerpo | Confirmado | Confirmado | Fusionado | El texto del chunk combina este encabezado con otros apartados. |
| III | `ESTRATEGIA DE DESARROLLO URBANO` | índice | cuerpo | Confirmado | Confirmado | Fusionado | Aparece concatenado con `II` y con las secciones siguientes. |
| 3.1 | `Estrategia de Integración al Ámbito Metropolitano` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.2 | `Estrategia Físico Natural` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.3 | `Estrategia Demográfica` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.4 | `Estructura Urbana` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.4.1 | `Usos del Suelo` | índice | cuerpo | Confirmado | Confirmado | No | En la salida del chunk no aparece `3.4.1` como subapartado independiente; la estructura de sección pierde precisión. |
| 3.5 | `Estructura Vial` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.6 | `Transporte` | índice | cuerpo | Confirmado | Confirmado | Omitido | El índice lo menciona, pero el JSON omite esa etiqueta y salta a `3.7`. |
| 3.7 | `Estacionamientos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.8 | `Infraestructura` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.9 | `Equipamiento y Servicios` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.10 | `Vivienda` | índice | cuerpo | Confirmado | Confirmado | Omitido | El índice lo menciona y el texto lo asume, pero el JSON no lo representa como sección independiente. |
| 3.11 | `Asentamientos Irregulares` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.12 | `Sitios Patrimoniales` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.13 | `Fisonomía Urbana` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 3.14 | `Espacio Público` | índice | cuerpo | Confirmado | Confirmado | Confirmado | El chunk fusiona el título con `IV. ORDENAMIENTO TERRITORIAL`. |
| IV | `ORDENAMIENTO TERRITORIAL` | índice | cuerpo | Confirmado | Confirmado | Fusionado | Se combina con el bloque previo en los chunks. |
| 4.1 | `Definición del Polígono de Aplicación del Programa Parcial` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 4.2 | `Zonificación` | índice | cuerpo | Confirmado | Confirmado | Omitido | El índice y el texto lo muestran explícitamente; el JSON salta de `4.1` a `4.3`. |
| 4.3 | `Normas de Ordenación` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 4.3.1 | `Normas de Ordenación ...` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 4.3.2 | `Normas Generales ...` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 4.3.3 | `Normas de Ordenación Particulares` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 4.4 | `Polígonos de Actuación` | índice | cuerpo | Confirmado | Confirmado | No | El chunk se fusiona con `V. ESTRATEGIA ECONÓMICA VI. ACCIONES ESTRATÉGICAS`. |
| V | `ESTRATEGIA ECONÓMICA` | índice | cuerpo | Confirmado | Confirmado | Fusionado | El chunk deja este encabezado unido con la siguiente sección. |
| VI | `ACCIONES ESTRATÉGICAS` | índice | cuerpo | Confirmado | Confirmado | Fusionado | El chunk deja este encabezado unido con el siguiente bloque. |
| 6.1 | `Programas de Desarrollo Urbano` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 6.2 | `Programas de Medio Ambiente` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |
| 6.3 | `Proyectos Urbanos Específicos` | índice | cuerpo | Confirmado | Confirmado | Confirmado | Se registra. |

## Hallazgos principales

### 1) Omitidos del índice representado

Los elementos faltantes o no aislados en el JSON son los siguientes:

- `1.8 Usos del Suelo`
- `1.14 Vivienda`
- `3.4.1 Usos del Suelo`
- `3.6 Transporte`
- `3.10 Vivienda`
- `4.2 Zonificación`
- `4.4 Polígonos de Actuación`
- `V. ESTRATEGIA ECONÓMICA`
- `VI. ACCIONES ESTRATÉGICAS`

### 2) Duplicados y mezclas por OCR / revisión

El documento incluye repetición del bloque de índice y fragmentos que se repiten a lo largo del texto. El chunk JSON remata claramente esos problemas:

- `II. IMAGEN OBJETIVO`, `III. ESTRATEGIA DE DESARROLLO URBANO` y `IV. ORDENAMIENTO TERRITORIAL` aparecen fusionados.
- `1.24.4 Pronóstico` queda unido a los encabezados de secciones siguientes.
- `3.14 Espacio Público` queda concatenado con `IV. ORDENAMIENTO TERRITORIAL`.
- `4.4 Polígonos de Actuación` queda fusionado con `V/VI`.

### 3) Numeración alterada / segmentación defectuosa

La ingesta automática está asignando muchos encabezados como un único texto, sin respetar la jerarquía de secciones y sin reconocer la diferencia entre cabezales de capítulo y encabezados de sección. Esto es una falla de representación y no una diferencia normativa.

### 4) Evidencia documental

La evidencia visible es directa y repetida:

- El PDF original presenta en el cuerpo del texto el bloque de índice con exactamente las secciones y sub-secciones antes descritas.
- `PPCU_Hipodromo_reviewed.txt` incluye el índice en 2 bloques (`ÍNDICE` y reaparición del mismo en el texto), lo que valida la duplicación por OCR/revisión.
- `PPCU_Hipodromo_reviewed_chunks.json` muestra el patrón de omisiones y fusiones descrito.

## Conclusión del índice

El índice del documento original es consistente en forma y contenido. La discrepancia principal no está en el PDF original, sino en la representación secundaria: la extracción/revisión y, sobre todo, el JSON de chunks, omiten varios encabezados y fusionan otros.

La evidencia confirma que el problema es de representación/documentación secundaria, no de la estructura jurídica del texto original.

## Decisión humana requerida

Se necesita confirmar si la auditoría debe tratar la numeración del índice como:

- A) una fuente documental que debe corregirse en los JSON (conservando el texto original y re-colocando los títulos), o
- B) una evidencia de que ciertos apartados no se desarrollan como secciones complejas y deben quedar representados como encabezados de contexto, no como capítulos separados.

La decisión es documental y editorial, no jurídica, y debe tomarse antes de la corrección de chunks.
