# Propuesta de esquema PostgreSQL para tablas del PPCU Hipódromo

## 1. Alcance

Este documento compara alternativas para almacenar en Aurora PostgreSQL datos tabulares del PPCU, recomienda un diseño futuro y describe consultas e ingestión conceptuales. No crea ni modifica tablas, archivos SQL o datos de Aurora. La propuesta se basa en `sql/001_initial_schema.sql`, el DDL embebido en `scripts/load_land_use_compatibility.py` y el código local; no se consultó la base de datos viva.

La Tabla 22 existente debe permanecer sin cambios mientras el usuario revisa sus registros `por validar`. La propuesta no aprueba los valores actuales ni determina su efecto jurídico.

## 2. Esquema y capacidad actual

### Esquema base declarado en SQL

`sql/001_initial_schema.sql` declara:

- `legal_documents`: instrumento documental, clave, nombre, tipo, jurisdicción, URL, fechas, versión y hash.
- `legal_chunks`: texto fragmentado, cita, sección/artículo, metadatos JSONB y `needs_review`.
- `legal_embeddings`: uno o más segmentos por chunk, vector `VECTOR(1024)`, modelo, metadatos JSONB y marca de revisión; relación compuesta con chunk y documento.

No hay tabla genérica de tablas documentales en ese SQL base.

### Tabla de compatibilidad existente

`scripts/load_land_use_compatibility.py` contiene DDL separado para `land_use_compatibility`. Su estructura guarda una fila por combinación actividad-zonificación, con `estado_original`, alias, archivo/páginas y `needs_review`. El cargador transforma 51 objetos × 7 zonificaciones en 357 celdas. La carga histórica de 357 celdas aparece documentada en Bitácora; el estado actual de Aurora no se verificó.

El DDL exige que `needs_review = TRUE`; permite literalmente `permitido`, `prohibido` y `por validar`; e indexa actividad, zona/estado y alias. No se encontró una FK a `legal_documents` ni un registro común de tabla. El script de carga no está incorporado en `001_initial_schema.sql`.

### Conclusión del diagnóstico

El esquema actual soporta chunks vectorizados y un caso estructurado particular. No alcanza para mantener un catálogo transversal de tablas ni la trazabilidad detallada por fila, columna, texto original, nota y estado de auditoría que requiere el diseño futuro.

### Identificadores actuales y homologación

En el SQL base, `legal_documents.id` es una llave primaria numérica generada internamente y `legal_documents.document_key` es `TEXT NOT NULL UNIQUE`, una clave estable de integración. `legal_chunks.document_id` es numérico y referencia `legal_documents.id`. `legal_embeddings` conserva los IDs numéricos de chunk/documento y usa una llave foránea compuesta para asegurar que corresponden al mismo documento.

El DDL actual de `land_use_compatibility`, por contraste, define `documento_id TEXT` (valor de integración `ppdu_hipodromo`) y `tabla_id TEXT`, sin FK a `legal_documents`. Por ello esos campos son claves textuales externas, no identificadores internos de base. La carga histórica de la tabla no prueba que exista actualmente en Aurora ni cuál sea su estado real: esta propuesta no se conectó a la base.

Convención futura recomendada:

- `id BIGINT` o tipo interno elegido por el esquema como PK numérica.
- `document_id BIGINT NOT NULL REFERENCES legal_documents(id)` en catálogo estructurado y relaciones internas.
- `document_key TEXT UNIQUE` en `legal_documents`, conservado en JSON, catálogo externo y exportaciones; no usarlo como sustituto de FK.
- `table_id TEXT` como clave documental estable (p. ej., `tabla_22`), distinta del `id` numérico de fila SQL y del número original impreso.
- `row_id`/`cell_id` internos numéricos y `row_key`/`cell_key` textuales deterministas para archivos, auditoría e idempotencia, si la implementación los requiere.
- Los IDs textuales existentes del cargador deben mapearse a `legal_documents.document_key`; una FK numérica debe resolver internamente la relación sin borrar ni renombrar las claves externas.

## 3. Alternativas consideradas

| Criterio | A. Una tabla genérica con datos JSONB | B. Tablas especializadas por tipo | C. Híbrido: metadatos comunes y estructuras especializadas |
|---|---|---|---|
| Facilidad de ingestión | Alta: cada fila se serializa a JSONB | Baja/Media: se requieren mapeos y validación por cada esquema | Media: catálogo común y adaptadores tipados donde el caso lo requiere |
| Mantenimiento | Un solo modelo, pero contratos JSON pueden divergir sin validación | Esquemas explícitos; cambios de documentos pueden exigir DDL | Balanceado; metadatos estables y payload especializado cuando aporta valor |
| Consultas SQL | Flexible, pero expresiones JSONB y tipos requieren cuidado; difícil imponer integridad | Sencillas y fuertemente tipadas para preguntas conocidas | Sencillas para casos especializados; JSONB útil para tablas heterogéneas |
| Rendimiento | Adecuado para lecturas pequeñas; filtros repetidos dentro de JSONB pueden requerir índices funcionales/GIN y validación | Mejor para filtros, joins y agregaciones recurrentes | Bueno en rutas de consulta clave; evita normalizar todo prematuramente |
| Trazabilidad | Puede quedar embebida en cada objeto, con riesgo de omisiones/inconsistencia | Puede ser completa si cada tabla repite procedencia | Un registro común de tabla más procedencia por fila/celda |
| Compatibilidad actual | Compatible con JSONB de metadatos existentes, pero es una nueva convención | `land_use_compatibility` demuestra un patrón específico ya presente | Reutiliza `land_use_compatibility` y agrega relación común en una fase autorizada |
| Complejidad para el MVP | Baja inicialmente, puede crecer en consultas ad hoc | Alta si se implementa para todo el inventario | Media; recomendable mantener el alcance actual y especializar solo lo necesario |

### A. Tabla genérica completamente JSONB

Una tabla puede almacenar `table_id`, número de fila, fuente, flags de revisión y `data JSONB`. Esto es simple para tablas cambiantes y contenido aún exploratorio. Sin embargo, consultas como “valor para zonificación X y actividad Y” dependen de rutas JSON, coerciones, estructura homogénea y sus índices. Cambios silenciosos en claves pueden romper consultas sin invalidar el dato. La trazabilidad también se vuelve vulnerable a diferencias entre objetos.

### B. Tablas SQL especializadas para cada familia

Esquemas como compatibilidad, estadísticas, normas por vialidad, restricciones patrimoniales y programación permiten tipos y consultas claros. A cambio, obligan a fijar modelos antes de terminar el cotejo del PDF, multiplican cargadores/migraciones y pueden representar mal tablas cuya función aún no está verificada. Crear una tabla por cada tabla documental sería aún más costoso y no está justificado por la evidencia disponible.

### C. Modelo híbrido recomendado

Mantener metadatos de procedencia/revisión comunes; conservar filas originales en una estructura flexible para familias todavía no estables; y usar relaciones tipadas para consultas jurídicas/operativas recurrentes. La compatibilidad de Tabla 22 permanece en su relación existente. La especialización adicional solo procede con la tabla confirmada, un patrón de consulta concreto y autorización explícita.

## 4. Recomendación

Se recomienda **C, híbrido y gradual**:

1. Reutilizar `legal_documents` como identidad del instrumento.
2. Añadir, solo en una futura migración aprobada, un catálogo de tablas documentales asociado a `legal_documents`, con número/título literal, páginas, hash del PDF, tipo funcional y estado de auditoría.
3. Para tablas heterogéneas aún no destinadas a consultas exactas recurrentes, conservar registros originales con JSONB más campos relacionales comunes de orden, página, texto y revisión.
4. Mantener `land_use_compatibility` como caso especializado para la Tabla 22; a futuro vincularla al catálogo con clave referencial y conservar cada celda/actividad y su procedencia sin borrar la forma original del JSON.
5. No diseñar aún tablas específicas para Tablas 1–21 o 24: primero confirmar visualmente título, estructura, unidades, notas y preguntas de recuperación.

Esta recomendación aprovecha el patrón ya existente de `legal_documents` / `legal_chunks` / JSONB y el caso de Tabla 22, evita una migración amplia antes de confirmar el inventario, y preserva SQL claro para las preguntas de compatibilidad. Ninguna de las tablas propuestas existe salvo las señaladas como existentes en el esquema/repositorio.

## 5. Modelo relacional conceptual propuesto

```text
legal_documents (id PK numérica, document_key UNIQUE textual)
  ├─ 1:N legal_chunks (document_id FK numérica) [actual]
  │      └─ 1:N legal_embeddings (FK numérica compuesta) [actual]
  └─ 1:N document_tables (document_id FK numérica) [propuesto]
           ├─ 1:N structured_table_rows (table_id FK numérica) [propuesto]
           │      └─ 1:N structured_table_cells (row_id FK numérica) [opcional/propuesto]
           ├─ 1:N table_notes (table_id FK numérica) [opcional/propuesto]
           └─ 1:N land_use_compatibility (table_id FK futura) [relación propuesta]
```

Entidades conceptuales:

- **`document_tables` (propuesta, no existente en el esquema inspeccionado):** `id` numérico PK; `document_id` numérico FK; `table_id` textual estable; `numero_original` y `titulo_literal`; páginas PDF/impresas; clase de dato; hash/versión fuente y estado de auditoría. Una restricción única futura debe evitar duplicar una clave textual dentro del documento sin renumerar lo impreso.
- **`structured_table_rows` (propuesta):** `id` numérico PK y `table_id` numérico FK; `row_key` textual estable opcional, orden, página, `texto_original`, `datos JSONB`, revisión y procedencia. Es la forma flexible para tablas cuya estructura no justifica aún columnas especializadas.
- **`structured_table_cells` (opcional/propuesta):** útil cuando se requiera buscar cada valor y columna por separado. Debe conservar `valor_original`, encabezado/código de columna, unidad y FK a fila; solo se justifica tras validar los casos de consulta.
- **`table_notes` (opcional/propuesta):** PK numérica, FK a tabla y vínculo opcional a fila/celda; texto literal, página y referencia de nota tal como se verificó.
- **`land_use_compatibility` (existente en el DDL del loader, no en `001_initial_schema.sql`):** hoy usa claves textuales `documento_id`/`tabla_id` y no FK. En el diseño futuro se recomienda agregar relación numérica a documento/tabla, manteniendo las claves legibles durante una migración compatibilizada.
- **`legal_chunks` / `legal_embeddings` (actuales en esquema base):** enlazados con FKs numéricas. Un identificador externo legible no reemplaza estas relaciones.

Todos los datos estructurados deben compartir contrato de evidencia, con localizador tipado (`legislativo`, `planeacion_urbana` o `tabla`) y referencias exactas de página/fila/celda cuando estén verificadas. No usar `article` para secciones decimales de programas urbanos. Deben mantener `needs_review` / estado de revisión. Valores normalizados coexisten con el original y nunca lo sustituyen.

### Clases de datos y columnas/payload

La estructura propuesta debe distinguir:

1. **Matriz cualitativa:** celdas con estado original literal, sin inferencias; Tabla 22 conserva su estructura especializada actual y sus flags.
2. **Parámetro normativo cuantitativo:** valor literal, unidad, zonificación/ámbito, localizador tipado y disposición de origen. No calcular porcentaje, superficie o densidad, ni convertir unidades.
3. **Estadística/diagnóstico:** valor literal, unidad, periodo, ámbito territorial y fuente. No crear agregados o indicadores derivados sin metodología explícita y autorizada.

Una fila flexible puede guardar los campos específicos en JSONB mientras la consulta no esté estabilizada, pero los atributos con filtros/restricciones recurrentes deben convertirse en columnas tipadas. Para todas las clases, conservar `texto_original`, referencia y revisión por separado de cualquier valor normalizado o interpretación del sistema.

## 6. Ejemplos SQL ilustrativos

Los ejemplos son conceptuales. `document_tables`, `structured_table_rows` y las columnas señaladas como comunes todavía no existen. En cambio, la consulta a `land_use_compatibility` refleja los nombres actuales, aunque la versión actual del helper `retrieve_land_use()` usa `psql` local y no forma parte del flujo Lambda.

### Tabla 22: actividad y zonificación

```sql
SELECT
    actividad_id,
    actividad_original,
    categoria,
    subcategoria,
    zonificacion,
    estado_original,
    fuente_archivo,
    fuente_paginas,
    needs_review AS pendiente_revision
FROM land_use_compatibility
WHERE documento_id = 'ppdu_hipodromo'
  AND tabla_id = 'tabla_22'
  AND zonificacion = :zonificacion
  AND (
      lower(actividad_original) = lower(:actividad)
      OR EXISTS (
          SELECT 1
          FROM jsonb_array_elements_text(alias_busqueda) AS a(alias)
          WHERE lower(a.alias) = lower(:actividad)
      )
  );
```

La consulta debe parametrizar valores de usuario. Un estado `por validar` se devuelve literalmente y no se convierte en permitido/prohibido. Cero resultados significa “sin coincidencia exacta”, no que la actividad esté prohibida.

### Catálogo de tabla (futuro)

```sql
SELECT table_id, numero_original, titulo_literal, paginas_pdf,
       tipo_funcional, estado_extraccion, needs_review
FROM document_tables
WHERE document_id = :document_id
  AND numero_original = :numero_original;
```

### Una fila de una tabla estadística/diagnóstica (futuro)

```sql
SELECT r.id AS row_id, r.row_order, r.page_pdf, r.original_text, r.data,
       r.footnote_refs, r.needs_review, r.audit_status
FROM structured_table_rows AS r
WHERE table_id = :table_id_numeric
  AND data ->> 'indicador' = :indicador;
```

El query JSONB es ilustrativo; si el indicador se vuelve un predicado central, conviene una columna tipada o una tabla especializada, no una cadena JSON ad hoc en toda la aplicación.

## 7. Ingestión conceptual

1. Validar rama, fuente PDF y los hashes; no ejecutar carga de datos reales durante la fase de diseño.
2. Confirmar visualmente cada tabla y su continuidad; catalogar por número/título original y páginas físicas e impresas si ambas se verifican.
3. Crear un JSON por tabla confirmada siguiendo la envolvente común y un `datos_estructurados` apropiado.
4. Validar con esquema/versionado, tipos, unicidad de identificadores, páginas positivas, referencias a notas y preservación de flags. Rechazar celdas incompletas dudosas; no “completar” con un valor predeterminado.
5. Revisar y aprobar humanamente el artefacto de ingestión. Mantener estados de revisión actuales; un proceso de importación no marca contenido como jurídicamente validado.
6. En futura operación autorizada: transacción, staging, comprobación de conteos/hash, inserción o actualización idempotente por clave documental y verificación de filas/celdas. No eliminar datos existentes salvo política de sincronización explícita.
7. Registrar resultado, fecha de ingesta, versión del JSON, SHA del PDF y auditoría.

El proceso actual `scripts/load_land_use_compatibility.py` valida el JSON y solo escribe con `--apply`; el modo por defecto no conecta a Aurora. Cualquier diseño futuro debe conservar ese principio de validación explícita y no ejecutar `--apply` sin autorización.

## 8. Decisiones pendientes

- Aprobar el modelo híbrido y el catálogo documental.
- Definir cuáles tablas, además de Tabla 22, tendrán preguntas que requieren SQL exacto.
- Confirmar estructura, celdas, unidades, notas y páginas a partir del PDF visualmente.
- Acordar si se conserva el texto/fila de origen como columnas directas, JSONB o ambas; recomendación: columnas comunes más copia original y datos tipados.
- Diseñar DDL/migraciones y políticas de actualización en una fase futura, separada de este diseño.
- Verificar en la base viva las tablas, tipos, constraints, claves, índices, conteos y estado real de `land_use_compatibility`; no se hizo conexión a Aurora.
- Comprobar colisiones/estabilidad de `document_key`, `documento_id`, `tabla_id` y los IDs del loader antes de proponer una FK o backfill.
- Confirmar nombres y compatibilidad PostgreSQL/Aurora para cualquier restricción, tipo o índice propuesto.
- Definir migración gradual: inspección y respaldo; mapeo validado de claves textuales a `legal_documents.id`; agregar FK numérica de forma compatible; validar relación y conteos; migrar consumidores; retirar claves redundantes solo después de autorización y verificación.
- Revisar por separado el localizador de páginas: los chunks actuales no conservan página exacta por fragmento.

## 9. Estrategia futura de migración de identificadores

No ejecutar hasta que la base viva y sus datos hayan sido inspeccionados y se autorice una migración:

1. Obtener snapshot/verificación aprobada de DDL, índices, constraints, conteos y muestras de claves de la base real; contrastar contra el repositorio y registrar diferencias.
2. Respaldar artefactos estructurados; verificar correspondencia unívoca entre `land_use_compatibility.documento_id` y `legal_documents.document_key`, sin asumir que todos los valores tienen correspondencia.
3. Diseñar una transición aditiva: tabla catálogo propuesta con PK numérica y FKs hacia `legal_documents.id`, conservando `document_key`/`table_id` textuales.
4. Crear/backfill de relaciones internas solo para filas con mapeo inequívoco; filas sin correspondencia se reportan y no reciben una FK ficticia.
5. Comprobar conteos, unicidad, orfandad, 51 actividades/357 celdas cuando se trate de Tabla 22, flags y valores literales.
6. Migrar los lectores/cargadores de forma compatible y mantener la referencia textual para integración/archivos externos.
7. Cambiar o retirar claves heredadas únicamente después de pruebas, aprobación y estrategia de reversión. No eliminar datos ni alterar Tabla 22 en el diseño presente.

La organización JSON se describe en [diseno_modelo_datos_PPCU.md](./diseno_modelo_datos_PPCU.md) y su consumo conceptual en [diseno_retriever_hibrido_PPCU.md](./diseno_retriever_hibrido_PPCU.md).

## Cambios de esta revisión

- Se aclaró la distinción existente y futura entre `id` numérico (PK/FK interna) y `document_key`/`table_id` textuales (identificadores externos estables).
- Se describieron las relaciones actuales de `legal_documents`, `legal_chunks` y `legal_embeddings`, frente al DDL independiente de `land_use_compatibility`, que hoy usa claves textuales sin FK.
- Se extendió el modelo híbrido a matrices cualitativas, parámetros normativos cuantitativos y estadísticas; se fijaron restricciones contra conversiones y cálculos derivados.
- Se incorporaron localizadores tipados y una estrategia de migración futura gradual, con validación de la base viva pendiente. No se creó DDL ni se ejecutó migración.
