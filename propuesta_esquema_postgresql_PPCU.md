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
legal_documents
  1 ─── N document_tables                 [propuesto, no existe]
             1 ─── N structured_table_rows [propuesto, no existe]
             1 ─── N table_notes           [opcional, propuesto, no existe]
             1 ─── N land_use_compatibility [relación futura; tabla ya definida por loader]

legal_documents
  1 ─── N legal_chunks
             1 ─── N legal_embeddings
```

Entidades conceptuales:

- **`document_tables` (propuesta):** identidad y metadatos comunes de una tabla original; única por documento e identificador original, sin renumerar.
- **`structured_table_rows` (propuesta):** registro/fila conservando orden, página, texto original y `data JSONB`; `data` no reemplaza los campos comunes ni los valores fuente.
- **`table_notes` (propuesta opcional):** notas con texto literal, página y vínculo a fila/celda o tabla cuando la referencia se pueda verificar.
- **`land_use_compatibility` (actual, creado por DDL del loader):** celdas estructuradas de la Tabla 22; su relación al catálogo sería una futura mejora, no parte del cambio actual.

Todos los datos estructurados deben tener una procedencia de documento/table/row y mantener `needs_review` / estado de revisión. Si se agregan valores normalizados, deben coexistir con la representación original y no sustituirla.

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
SELECT row_id, row_order, page_pdf, original_text, data,
       footnote_refs, needs_review, audit_status
FROM structured_table_rows
WHERE table_id = :table_id
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

La organización JSON se describe en [diseno_modelo_datos_PPCU.md](./diseno_modelo_datos_PPCU.md) y su consumo conceptual en [diseno_retriever_hibrido_PPCU.md](./diseno_retriever_hibrido_PPCU.md).
