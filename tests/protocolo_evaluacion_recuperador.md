# Protocolo de evaluación del recuperador — Todo Derecho Vecino

**Versión:** 1.0, propuesta  
**Fecha:** 27 de octubre de 2026  
**Ámbito:** Recuperación semántica de fragmentos del corpus jurídico del MVP  
**Estado:** Propuesto; pendiente de integrar y validar en el repositorio

## 1. Propósito

Establecer un procedimiento repetible para evaluar si el recuperador devuelve fragmentos pertinentes, completos, trazables y adecuados para responder preguntas sobre los instrumentos jurídicos incluidos en el MVP de Todo Derecho Vecino.

La evaluación separa cuatro aspectos: funcionamiento técnico, pertinencia de recuperación, integridad de las referencias y validación jurídica. Aprobar uno no implica aprobar los demás.

## 2. Alcance y restricciones

La evaluación se limita a los cinco instrumentos jurídicos definidos para el MVP:

1. Programa Parcial de Desarrollo Urbano de la colonia Hipódromo.
2. Programa de Desarrollo Urbano de la alcaldía Cuauhtémoc.
3. Ley de Establecimientos Mercantiles de la Ciudad de México.
4. Ley de Desarrollo Urbano del Distrito Federal.
5. Ley de Cultura Cívica de la Ciudad de México.

Las pruebas no deben ampliar silenciosamente el corpus ni tratar una sección, tabla o cuadro urbanístico como si necesariamente fuera un artículo legal.

Durante la evaluación se mantendrán `needs_review = true` y `pendiente_revision = true`. La evaluación técnica no autoriza conclusiones jurídicas definitivas.

## 3. Tipos de evaluación

### 3.1. Pruebas estructuradas

Comprueban los comportamientos explícitos de `retrieve_land_use()`, incluidos los estados originales de zonificación y la marca de revisión.

La batería inicial contiene 11 casos. El criterio de aceptación es que los 11 casos pasen. Cualquier fallo debe identificarse y explicarse; no se debe cambiar el resultado esperado solo para hacer pasar una prueba sin justificar primero la corrección.

### 3.2. Pruebas semánticas

Comprueban si `retrieve()` devuelve fragmentos útiles para responder las preguntas de la batería fija. La batería inicial contiene 16 consultas, con cinco resultados por consulta.

Cada resultado se anota manualmente usando la siguiente escala:

- **2 — Relevancia directa:** el fragmento aporta evidencia sustantiva para responder la pregunta.
- **1 — Relevancia parcial:** aporta contexto relacionado, pero no basta para responder la pregunta completa.
- **0 — Irrelevante:** no aporta evidencia útil para la pregunta concreta.

La pertinencia debe juzgarse respecto de la pregunta, no solo porque el resultado pertenezca al documento correcto o mencione palabras parecidas.

Las anotaciones deben conservar la pregunta, la ejecución, el identificador del chunk, la posición del resultado, la etiqueta y una justificación breve. Los desacuerdos relevantes deben revisarse antes de consolidar la referencia de evaluación.

## 4. Métricas

### Precision@5

Se calcula como el número de resultados con etiqueta 1 o 2 entre los primeros cinco resultados, dividido entre cinco. La precisión agregada del conjunto se calcula sumando los resultados pertinentes de todas las consultas y dividiendo entre el número total de posiciones evaluadas.

Los resultados parciales cuentan como pertinentes para esta métrica, pero se reportan por separado para que no oculten una baja proporción de evidencia directa.

### Relevancia directa

Se reporta el porcentaje de resultados con etiqueta 2 dentro de las primeras cinco posiciones. Permite distinguir la evidencia directamente útil del contexto solamente parcial.

### Cobertura de consultas

Se reporta el porcentaje de preguntas que obtienen al menos un resultado con etiqueta 1 o 2 en el top 5. También se identifica por separado cualquier consulta sin resultados pertinentes.

### MRR@5

El Mean Reciprocal Rank se calcula usando la primera posición que tenga etiqueta 2. Si no existe ningún resultado de relevancia directa entre los cinco primeros, la contribución de esa consulta es cero. Para cada consulta, el valor es el inverso de la posición de ese primer resultado directo; después se calcula el promedio.

### Integridad de fuente y cita

Se verifica que el resultado identifique correctamente el documento y que la cita, el artículo, la sección, la tabla o la página correspondan a la fuente original. Una referencia incorrecta o imposible de comprobar debe registrarse como defecto, aunque el texto parezca semánticamente pertinente.

### Calidad de fragmentos

Se inspecciona el contenido completo del chunk, no solamente una vista truncada en consola. Se registran pérdida de contexto, cortes a mitad de oración o tabla, mezcla de contenidos no contiguos, encabezados ausentes, referencias equivocadas y extracción tabular defectuosa.

## 5. Criterios propuestos de éxito

La aceptación se realiza por etapas. Los siguientes umbrales son una propuesta inicial que debe aprobarse y versionarse antes de usarse como criterio oficial.

### Puerta A: funcionamiento técnico

- Las 11 pruebas estructuradas pasan.
- La ejecución semántica finaliza sin errores no controlados.
- Cada resultado puede vincularse con su consulta y su chunk de origen.
- Los errores, las consultas sin resultados y los resultados incompletos quedan registrados.

### Puerta B: recuperación semántica

En la batería fija de 16 consultas:

- Precision@5 agregada de al menos **80 %**, considerando relevantes las etiquetas 1 y 2.
- Al menos **14 de las 16 consultas** recuperan uno o más resultados con etiqueta 1 o 2.
- MRR@5 de al menos **0.75**, calculado con la primera etiqueta 2.
- Los resultados directos y parciales se reportan por separado; no se acepta ocultar una caída de relevancia directa detrás de un aumento de resultados parciales.
- Las métricas se presentan globalmente y por instrumento o grupo de consultas cuando el tamaño de la muestra lo permita.

Estos umbrales sirven como puerta de aceptación del conjunto de regresión, no como prueba estadística de calidad general ni como garantía de que el recuperador responderá correctamente a preguntas no evaluadas.

### Puerta C: integridad de resultados

- El 100 % de los resultados usados como evidencia principal en los casos aprobados tiene una fuente y una referencia localizables.
- No quedan errores críticos conocidos de atribución de documento, artículo o sección en los resultados aceptados.
- Los fragmentos relevantes conservan el contexto necesario para interpretar la disposición o el dato urbanístico.
- Las tablas y cuadros mantienen sus encabezados, valores, estados originales y procedencia cuando sean necesarios para interpretar el resultado.

### Puerta D: control de regresiones

- Se ejecuta la misma batería antes y después de cada cambio.
- Se conservan las métricas y las anotaciones de la línea base.
- Ningún cambio se acepta solo porque mejore una consulta aislada: se comparan los resultados del conjunto completo.
- Cualquier regresión importante se documenta y se corrige o se acepta explícitamente con justificación.

### Puerta E: revisión jurídica

- Se comprueba la correspondencia con la fuente normativa original.
- Se revisan la cita, la ubicación y la vigencia de las disposiciones antes de usarlas como fundamento jurídico confirmado.
- Se mantienen las marcas de revisión pendientes hasta completar la validación correspondiente.

El recuperador solo podrá declararse **técnicamente aceptado para la batería de regresión** cuando supere las puertas A, B, C y D. La validación jurídica es una condición separada para presentar los resultados como fundamentos normativos confirmados.

## 6. Registro reproducible de cada ejecución

Cada ejecución debe tener un identificador único y conservar:

- Fecha y hora, rama y commit evaluado.
- Versión de la batería y conjunto de anotaciones utilizado.
- Configuración del recuperador y valor de `top_k`.
- Modelo de embeddings, versión disponible, dimensión y configuración de distancia, cuando estos datos puedan verificarse.
- Consulta original y resultados completos, ordenados por posición.
- Identificadores de chunks, documento, localizador legal, puntuaciones y metadatos disponibles.
- Errores de ejecución y consultas sin resultados.
- Etiquetas manuales, justificación y versión de las anotaciones.
- Métricas calculadas y comparación con la línea base.

Los resultados de una ejecución no deben sobrescribirse al ejecutar de nuevo el sistema. Las anotaciones deben apuntar a la ejecución y al resultado exactos que se evaluaron.

## 7. Procedimiento de evaluación

1. Confirmar el estado del repositorio, la versión de la batería y la disponibilidad del entorno de prueba.
2. Ejecutar las pruebas estructuradas y semánticas sin modificar el recuperador.
3. Guardar los resultados completos en un formato legible por máquina, preferentemente JSON.
4. Anotar los resultados semánticos usando la escala 0, 1 y 2.
5. Calcular las métricas y comparar con la línea base.
6. Inspeccionar los defectos de mayor impacto, empezando por trazabilidad, extracción, chunking, metadatos y asociación de embeddings.
7. Formular una hipótesis concreta y cambiar una etapa a la vez cuando sea posible.
8. Repetir la batería completa y documentar mejoras y regresiones.
9. Revisar la integridad de las citas y la vigencia normativa antes de cerrar la validación.

Si Aurora no está disponible, se pueden revisar archivos, scripts y artefactos locales. Las pruebas que dependan de datos o servicios de Aurora deben quedar marcadas como pendientes; no se deben presentar resultados históricos como una ejecución nueva.

## 8. Línea base inicial

La ejecución del 26 de octubre de 2026 registró:

- Pruebas estructuradas: 11/11 aprobadas.
- Consultas semánticas: 16.
- Resultados semánticos anotados: 80.
- Etiqueta 2: 21 resultados.
- Etiqueta 1: 24 resultados.
- Etiqueta 0: 35 resultados.
- Precision@5 agregada provisional: 45/80 = 56.25 %.
- Consultas sin resultados pertinentes en el top 5: 1.

La línea base no alcanza el umbral propuesto de Precision@5 del 80 %. Además, la salida de consola trunca los fragmentos a 500 caracteres, por lo que es necesario conservar y revisar el contenido completo antes de atribuir todos los cortes observados al chunking.

## 9. Pendientes antes de declarar el protocolo vigente

- Verificar que las etiquetas y su orden coincidan con los resultados completos de la ejecución registrada.
- Acordar y versionar los umbrales de aceptación.
- Implementar el guardado reproducible de resultados y métricas.
- Auditar la correspondencia entre chunks y embeddings, sin asumir que una diferencia de conteos constituye por sí sola un error.
- Mantener intactas las fuentes originales y las marcas de revisión jurídica.

**Regla final:** ningún cambio del recuperador se considera exitoso por intuición, por mejorar un solo ejemplo o por aumentar la cantidad de resultados. Debe mejorar la batería de regresión bajo métricas explícitas, preservar la trazabilidad y no introducir regresiones críticas.

