# Inventario de tablas, cuadros, figuras y elementos gráficos — PPCU Hipódromo

**Revisión editorial:** 2026-11-12. Se precisó el estado de la Tabla 23 sin modificar el inventario de los demás elementos.

## Alcance

Este inventario revisa visualmente el documento base y compara los elementos gráficos textualmente citados para determinar si son tablas, cuadros estadísticos, mapas o figuras, y si se han extraído adecuadamente.

## Archivos auditados

| Archivo | SHA256 | Tamaño | Tipo | Observación |
|---|---|---:|---|---|
| `leyes_cdmx/PPCU_Hipodromo.pdf` | `aec2baafa3dcd3fcdcccccf60ea78128c3621c39554bc9e048ce3e47a86309d5` | 1,232,772 bytes | PDF original | Documento base; 122 páginas. |
| `leyes_cdmx/PPCU_Hipodromo_extracted.txt` | `25636a080051321a8e686939d34187ee2c350ce9948f992efbe1d915d058390d` | 373,389 bytes | texto extraído | Identifica tablas por nombre y contexto. |
| `leyes_cdmx/PPCU_Hipodromo_reviewed.txt` | `49770bd6c72bc7785d7e89bdf9c017a96358741adc4ac79f18ca2f4590ea61fd` | 277,021 bytes | texto revisado | Conserva la referencia textual a tablas y cuadros. |

## Inventario principal

| Número | Título literal | Página inicial | Página final | Tipo de elemento | Notas y observaciones | Estado de extracción |
|---|---|---|---|---|---|---|
| 1 | `Mezcla de usos del suelo en el Distrito I` | no confirmada | no confirmada | Tabla estadística / diagnóstico | Aparece como una tabla de diagnóstico espacial, no de compatibilidad de uso. | Detectada en texto extraído; no en JSON de compatibilidad. |
| 2 | `Mezcla de usos del suelo en el Distrito II` | no confirmada | no confirmada | Tabla estadística / diagnóstico | Misma naturaleza que la Tabla 1. | Detectada. |
| 3 | `Mezcla de usos del suelo en el Distrito III` | no confirmada | no confirmada | Tabla estadística / diagnóstico | Se usa para caracterización del distrito. | Detectada. |
| 4 | `Mezcla de usos del suelo en el Distrito IV` | no confirmada | no confirmada | Tabla estadística / diagnóstico | Aparece en la sección de diagnóstico. | Detectada. |
| 5 | `Mezcla de usos del suelo en el Distrito V` | no confirmada | no confirmada | Tabla estadística / diagnóstico | Tipo de uso de suelo por segmento. | Detectada. |
| 6 | `Mezcla de usos del suelo en el Distrito VI` | no confirmada | no confirmada | Tabla estadística / diagnóstico | En el mismo bloque de diagnóstico. | Detectada. |
| 7 | `Oferta y demanda por Distritos` | no confirmada | no confirmada | Cuadro comparativo | Cuadro de oferta y demanda; no es una tabla de zonificación. | Detectada. |
| 8 | `Equipamiento. Subsistema Salud` | no confirmada | no confirmada | Tabla de diagnóstico / servicios | Registra dotación sanitaria. | Detectada. |
| 9 | `Equipamiento. Subsistema Educación` | no confirmada | no confirmada | Tabla de diagnóstico / servicios | Se continúa en la siguiente página (aparece `Continúa Tabla 9`). | Detectada. |
| 10 | `Equipamiento. Subsistema Servicios Urbanos` | no confirmada | no confirmada | Tabla de diagnóstico / servicios | Registro de servicios urbanos. | Detectada. |
| 11 | `Equipamiento. Subsistema Administración Pública` | no confirmada | no confirmada | Tabla de diagnóstico / servicios | Se observa como tabla de servicios públicos. | Detectada. |
| 12 | `Tendencia decreciente de la población` | no confirmada | no confirmada | Tabla demográfica | No es una tabla de zonificación ni compatibilidad; describe demografía. | Detectada. |
| 13 | `Tabla comparativa de ocupación por vivienda` | no confirmada | no confirmada | Tabla estadística / vivienda | Relevante para diagnóstico. | Detectada. |
| 14 | `Tipo de vivienda` | no confirmada | no confirmada | Tabla estadística / vivienda | Diagnóstico de vivienda. | Detectada. |
| 15 | `Materiales utilizados en la construcción de vivienda` | no confirmada | no confirmada | Tabla estadística / vivienda | Es un cuadro técnico de construcción. | Detectada. |
| 16 | `Número de cuartos en la vivienda` | no confirmada | no confirmada | Tabla estadística / vivienda | Registro de tamaño y composición del hogar. | Detectada. |
| 17 | `Tenencia` | no confirmada | no confirmada | Tabla estadística / vivienda | Se refiere a tenencia de predios y viviendas. | Detectada. |
| 18 | `Vacantes urbanas` | no confirmada | no confirmada | Tabla diagnóstica / suelo | Relevante para el diagnóstico y la ocupación del suelo. | Detectada. |
| 19 | `Uso predominante del suelo en edificios catalogados` | no confirmada | no confirmada | Tabla de diagnóstico / patrimonio | Tiene valor patrimonial y de uso del suelo. | Detectada. |
| 20 | `Normatividad por vialidad` | no confirmada | no confirmada | Tabla normativa / vialidad | Tiene función normativa y se continúa en la siguiente página. | Detectada. |
| 21 | `Tendencias programáticas de población` | no confirmada | no confirmada | Tabla demográfica / programa | Modelo para estimaciones del programa. | Detectada. |
| 22 | `TABLA DE COMPATIBILIDAD DE USOS DEL SUELO` | 80 | 81 | Tabla de zonificación y compatibilidad | Es la tabla de compatibilidad que se usa en el JSON `tabla_22.json`. | Detectada en PDF, texto extraído y JSON asociado. |
| 23 | `Tabla 23` | no localizada | no localizada | Elemento no localizado; existencia no determinada | No se encontró una referencia con ese número en el texto extraído consultado. No se documenta una inspección visual exhaustiva de las 122 páginas para resolver su existencia. | No localizada; no se concluye inexistencia. |
| 24 | `Tipo de intervencion segun niveles de protección` | no confirmada | no confirmada | Tabla de normas / protección | Tablas de intervención por nivel de protección. | Detectada. |
| — | `Mapa Mental` | no confirmada | no confirmada | Figura / ejercicio participativo | Recurso gráfico no tabular; aparece como ejercicio de consulta ciudadana. | Detectada textual y tipificada como figura. |
| — | `Gráfica 24. Población residente y flotante en día hábil` | no confirmada | no confirmada | Figura / gráfica | Se distingue de una tabla técnica; la referencia es gráfica, no tabular. | Detectada textual. |
| — | `TABLA DE PROGRAMA DE ACCIONES PRIORITARIAS` | no confirmada | no confirmada | Tabla programática | Aparece mucho más adelante; es una tabla de acciones/objetivos. | Detectada como tabla programática, no de compatibilidad. |

## Observaciones relevantes de inventario

### 1) Clasificación funcional

Las tablas no son homogéneas. El documento mezcla varias funciones:

- Tablas de zonificación y compatibilidad: `Tabla 22`.
- Cuadros estadísticos y diagnósticos: `Tablas 1-19`, `21`.
- Tablas normativas: `Tabla 20` y `Tabla 24`.
- Tablas de programas de acción: `TABLA DE PROGRAMA DE ACCIONES PRIORITARIAS`.
- Figuras y mapas: `Mapa Mental`, `Gráfica 24`.

### 2) Tabla 23: no localizada (existencia no determinada)

En el texto extraído consultado no se encontró una referencia a `Tabla 23`; en esa representación, la numeración pasa de la `Tabla 22` a la `Tabla 24`. Ese salto no demuestra por sí solo que la Tabla 23 no exista en el PDF. La revisión disponible no documenta una inspección visual exhaustiva de las 122 páginas que permita descartar su presencia. Por tanto, el estado correcto es **no localizada**; no debe describirse como ausencia real ni como inexistencia confirmada.

### 3) Esquema de extracción

La extracción primaria y la revisión del texto detectan tablas, pero no siempre las normalizan como elementos independientes. De manera especial:

- La `Tabla 22` está identificada como elemento separado en los materiales descritos por este inventario. Su contenido y estado de revisión se controlan en la auditoría específica de Tabla 22.
- Las tablas funcionales de diagnóstico (`1-21`) aparecen en el texto extraído y revisado con buena continuidad.
- El archivo `PPCU_Hipodromo_reviewed_chunks.json` no modela estas tablas como una colección separada; modela secciones y chunks del texto, no el conjunto completo de tablas del documento.

### 4) Relevancia para la corrección posterior

Antes de corregir chunks o JSON derivados, debe confirmarse si el objetivo de la etapa siguiente es:

- A) normalizar la estructura narrativa del documento, o
- B) normalizar la estructura documental que incluye tablas, cuadros y figuras como elementos distintos del cuerpo legal y normativo.

La tabla 22 se integra a la lógica de compatibilidad de usos de suelo y puede recopilarse exactamente como una estructura de datos; las otras tablas cumplen otras funciones, por lo que no deben tratarse idénticamente en el mismo pipeline de “compatibilidad”.
