Bitácora — Todo Derecho Vecino
Ruta de trabajo (v4) — fases del proyecto

Acordada al retomar el repo todo-derecho-vecino como línea base. Código antes que AWS: el preprocesamiento y la FSM de WhatsApp no dependen de infraestructura en la nube y provisionar Aurora/Fargate antes de tener el corpus y el esquema validados arriesga tener que rehacer la infraestructura a medias.

Fase	Foco	Qué se hace	Depende de AWS	Estado
0. Preparación	—	Revisión manual de OCR (_reviewed.txt); en paralelo, iniciar verificación del número de WhatsApp Business en Meta	No	✅ Completada
1. Preprocesamiento — orquestador y chunking	Preprocesamiento	legal_document_processor.py: chunking por artículo/fracción, enriquecido con autoridad_ner.py y procedimiento_ner.py, esquema de metadatos completo	No	✅ Completada (18/20 documentos sólidos; PDDU/PPCU pendientes de limpieza manual)
2. RAG local (sin Bedrock ni Aurora)	Preprocesamiento	Cargar los JSON de chunks en un vector store local, validar retrieval + cita exacta, iterar el prompt de generación con la API de Claude directamente	No	🔵 En curso
3. Integración WhatsApp — FSM	WhatsApp	Adaptar la FSM de AgentesMX (estados, validators.py, router.py) al dominio legal; migrar el canal de Twilio a Meta Cloud API; correr local con ngrok	No	⬜ Pendiente
4. Entorno AWS	Infraestructura	Terraform (red, IAM, Aurora Serverless v2 + pgvector con el esquema ya validado, Fargate), CI/CD, migración de embeddings del vector store local a pgvector	Sí	⬜ Pendiente
5. Corte a producción	Infraestructura	Multi-AZ, monitoreo con alertas, simulacro de failover, mx-central-1, AWS Budgets	Sí	⬜ Pendiente
Completado
legal_document_processor.py construido y validado contra el corpus real (no contra datos de prueba):
Chunking por artículo/fracción para leyes y reglamentos, con metadatos (título/capítulo/sección, cita_legal, fechas de publicación/reforma extraídas del propio texto).
Tres correcciones al regex de detección de artículos, cada una encontrada probando contra texto real, no a priori:
El patrón capturaba referencias cruzadas dentro del texto ("de conformidad con el artículo 11...") — se corrigió exigiendo puntuación de cierre inmediata después del número.
Algunos documentos usan "ARTÍCULO" en mayúsculas — se hizo insensible a mayúsculas/minúsculas.
Algunos documentos usan "Artículo N." (solo punto) en vez de "Artículo N .-" (con guion) — se quitó la exigencia del guion y en su lugar se añadió validación de secuencia ascendente para seguir filtrando referencias cruzadas.
Modo de lote (--batch documentos_config.json) para procesar todo el corpus con un solo comando, saltando sin error los documentos que aún no tienen _reviewed.txt.
Rama especializada para Programas de Desarrollo Urbano (PDDU/PPCU), que no usan "Artículo N." sino secciones numeradas con decimales (4.3.1, 4.4.2...); incluye limpieza de bloques de índice interno que interferían con la detección de secciones.
18 de 20 documentos del corpus procesados con resultados sólidos: ~7,200+ fragmentos generados entre leyes y reglamentos, cada uno con cita_legal verificable.
documentos_config.json armado y depurado: 20 documentos, con corrección de varios nombres de archivo que no coincidían entre el config y el disco (acentos, espacios, versiones de documento distintas a las anotadas originalmente).
Pendiente
 Completar las URLs reales de la Gaceta Oficial en documentos_config.json — los 20 documentos siguen con "fuente": "PENDIENTE: URL de la Gaceta Oficial". Buscar en data.consejeria.cdmx.gob.mx.
 Limpiar manualmente los bloques de índice duplicados en PPCU Hipódromo — se detectó que la numeración de secciones (1.1 a 8.4) aparece repetida en al menos tres pasadas distintas dentro del mismo documento, lo que confunde el chunker automático. Revisar durante la pasada de OCR y eliminar los bloques de índice que no tengan desarrollo de contenido real debajo.
 Regenerar el JSON de PDDU-Cuauhtémoc con el título correcto — se procesó por error con --titulo "Programa Parcial de Desarrollo Urbano Hipódromo" (el título de PPCU, no el suyo).
 Confirmar que las versiones de dos documentos son las correctas, no un desfase accidental de descarga:
Ley Orgánica de Alcaldías: el config original decía v6.1, el archivo real es v6.4.
Reglamento de la Ley de Establecimientos Mercantiles: el config original decía v2, el archivo real es v1.
 Validar autoridad_ner.py (spaCy + es_core_news_sm) en el entorno local — no se pudo probar en el entorno de Claude; confirmar que sujetos_obligados se llena correctamente al correr el pipeline completo.
 Afinar la heurística de tipo_disposicion — actualmente casi el 100% de los fragmentos del corpus quedan marcados needs_review: true; conviene revisar ejemplos reales de varias leyes para mejorar las reglas léxicas.
 Revisión manual de calidad: inspeccionar una muestra de chunks de cada documento contra el PDF original, con prioridad en PDDU/PPCU (mayor tasa de error esperada que en las leyes).
 Fase 2 del roadmap: motor RAG local (retrieval + generación con citas) sobre los 18 documentos ya validados, antes de tocar infraestructura de AWS.
Decisiones tomadas
documentos_config.json se mantiene con solo 4-5 campos por documento (reviewed_path, titulo, fuente, tipo_documento, y opcionalmente autoridad_principal). Se decidió no agregar palabras clave, autoridades ni procedimientos a nivel de documento completo: esa información varía por artículo/fracción, no por ley, y ya está contemplada como salida automática por fragmento dentro de legal_document_processor.py (tema_principal, sujetos_obligados, tipo_disposicion). Agregarla al config duplicaría trabajo manual en un nivel de detalle menos útil que el automático.

## Actualización del proyecto – Definición del MVP y estado de desarrollo
### Octubre de 2026

### 1. Reorientación y cierre del alcance del MVP

Se decidió desarrollar una versión acotada de **Todo Derecho Vecino** para la estancia de 10 semanas en INFOTEC–CENIDET. El objetivo del MVP es construir el núcleo funcional indispensable: un asistente capaz de recibir una consulta sobre uso de suelo, recuperar información pertinente de un corpus jurídico controlado y generar una respuesta fundamentada con cita a la fuente normativa.

El alcance mantiene como componentes principales una interfaz web sencilla, un backend serverless, un motor RAG, un almacén vectorial basado en Aurora PostgreSQL con pgvector, un único modelo de lenguaje, infraestructura definida mediante Terraform y registros básicos mediante CloudWatch. Las funcionalidades adicionales se mantienen como trabajo futuro y no constituyen requisitos para el cierre del MVP.

Esta delimitación es consistente con el documento de alcance de la estancia, cuyo criterio es conservar únicamente lo indispensable para que el asistente responda preguntas con base en el corpus jurídico y cite sus fuentes. [Referencia: documento de alcance funcional a 10 semanas.]

### 2. Corpus jurídico definitivo del MVP

Como decisión de diseño se estableció un corpus jurídico específico de cinco instrumentos relacionados con las consultas de uso de suelo y convivencia urbana en la Ciudad de México:

1. Programa Parcial de Desarrollo Urbano de la colonia Hipódromo.
2. Programa de Desarrollo Urbano de la Alcaldía Cuauhtémoc.
3. Ley de Establecimientos Mercantiles de la Ciudad de México.
4. Ley de Desarrollo Urbano del Distrito Federal.
5. Ley de Cultura Cívica de la Ciudad de México.

La selección de cinco instrumentos representa una modificación respecto de la indicación inicial del documento de alcance, que planteaba seleccionar entre dos y tres normas prioritarias. Se decidió ampliar el corpus a cinco porque permite cubrir de manera más adecuada las diferentes dimensiones normativas que intervienen en las consultas previstas para el MVP.

Los documentos jurídicos adicionales que ya existen en el proyecto no se consideran eliminados. Se mantienen como posible corpus ampliado para una etapa posterior, mientras que el desarrollo y la evaluación del MVP se concentrarán en los cinco instrumentos definidos.

### 3. Arquitectura simplificada adoptada

Se decidió utilizar una arquitectura deliberadamente sencilla para reducir la complejidad de implementación y concentrar el esfuerzo en el funcionamiento del RAG y la fundamentación jurídica.

La arquitectura objetivo queda definida de la siguiente manera:

Usuario
  ↓
Frontend web estático
  ↓ HTTPS/JSON
API Gateway
  ↓
AWS Lambda
  ├── procesamiento de la consulta
  ├── generación/uso del embedding
  ├── recuperación de fragmentos relevantes
  ├── construcción del prompt
  ├── llamada al modelo de lenguaje
  └── construcción de la respuesta con cita normativa
  ↕
Aurora PostgreSQL Serverless v2 + pgvector
  ↕
Amazon Bedrock / modelo de lenguaje
  ↓
Respuesta fundamentada

Además:

S3 → almacenamiento de documentos originales y artefactos de ingesta
CloudWatch → registros básicos
IAM → control de permisos y mínimo privilegio

Se decidió utilizar una sola función Lambda como orquestador en lugar de dividir prematuramente el sistema en múltiples microservicios. También se decidió mantener un frontend web estático sencillo y utilizar un solo modelo de lenguaje durante el MVP.

### 4. Decisiones de infraestructura y seguridad

La infraestructura AWS se está definiendo mediante Terraform para que pueda reproducirse a partir del código y no dependa de configuraciones manuales.

Se establecieron las siguientes decisiones:

- VPC dedicada para el proyecto.
- Subredes privadas para los recursos que no necesitan exposición pública.
- Aurora PostgreSQL Serverless v2 en configuración Single-AZ.
- Extensión pgvector para almacenamiento y búsqueda vectorial.
- S3 para almacenamiento de documentos.
- IAM con principio de mínimo privilegio para los recursos de aplicación.
- Cifrado en reposo utilizando las capacidades administradas de AWS.
- CloudWatch para registros básicos.
- Uso de MFA y controles de seguridad de la cuenta AWS.
- AWS Budgets y Cost Anomaly Detection como mecanismos de control de costos.
- Se evita incorporar durante el MVP servicios y mecanismos que no son indispensables, como Multi-AZ, WAF, Shield, Object Lock, separación staging/producción y sistemas avanzados de recuperación ante desastres.

### 5. Organización del desarrollo mediante una rama específica

Se decidió mantener el repositorio existente:

https://github.com/iasalazar1/todo-derecho-vecino

en lugar de crear un repositorio nuevo.

Para aislar el desarrollo correspondiente a la estancia se creó la rama:

mvp-estancia

La rama fue creada a partir de `main` y ya se encuentra publicada en GitHub. El desarrollo del MVP de la estancia continuará en esta rama, manteniendo `main` como línea principal del proyecto.

La estrategia permite conservar el trabajo previo del proyecto y, al mismo tiempo, mantener identificable el desarrollo específico del MVP de 10 semanas.

### 6. Avances técnicos realizados

Antes de la definición final del MVP ya existía trabajo de procesamiento del corpus jurídico, incluyendo extracción, estructuración y fragmentación de documentos legales. El proyecto cuenta con código para el procesamiento de documentos y generación de chunks con metadatos jurídicos.

También se avanzó en la infraestructura AWS mediante Terraform. Se definieron recursos base de red, almacenamiento e IAM y posteriormente se incorporó la infraestructura necesaria para la base de datos.

Durante la Semana 3 se desplegó Aurora PostgreSQL Serverless v2 en configuración Single-AZ, con PostgreSQL compatible y configuración Serverless v2. Se configuró una instancia `db.serverless` y se estableció la infraestructura necesaria para permitir el acceso controlado desde el entorno de prueba.

Para las pruebas de administración y conectividad se incorporó temporalmente una instancia EC2 de prueba con acceso mediante AWS Systems Manager, junto con los endpoints necesarios y una regla controlada para permitir la conexión hacia Aurora por el puerto 5432. Esta infraestructura tiene carácter de apoyo al desarrollo y deberá revisarse posteriormente para mantener únicamente los recursos necesarios para el MVP.

### 7. Estado actual

El proyecto se encuentra en una transición entre la infraestructura base y la implementación del flujo RAG sobre AWS.

Los principales elementos ya definidos o avanzados son:

- Alcance funcional del MVP.
- Corpus jurídico objetivo.
- Arquitectura AWS simplificada.
- Estrategia de ramas y control de versiones.
- Infraestructura base mediante Terraform.
- VPC y subredes.
- Almacenamiento S3.
- Roles y controles IAM.
- Aurora PostgreSQL Serverless v2.
- Infraestructura inicial para pruebas de conectividad.
- Procesamiento y fragmentación preliminar del corpus jurídico.

El siguiente objetivo técnico es completar la preparación del corpus seleccionado, diseñar y validar el esquema de datos jurídico en PostgreSQL/pgvector y realizar la ingesta y vectorización del corpus del MVP.

### 8. Próximos pasos

La prioridad inmediata es continuar con la Semana 4 del cronograma:

1. Confirmar los cinco documentos que constituyen el corpus del MVP.
2. Revisar y normalizar los documentos jurídicos seleccionados.
3. Definir el esquema definitivo de documentos, fragmentos y metadatos jurídicos.
4. Implementar o adaptar el proceso de chunking para el corpus definitivo.
5. Generar los embeddings.
6. Cargar los fragmentos y vectores en Aurora PostgreSQL con pgvector.
7. Ejecutar consultas de similitud para verificar la recuperación.
8. Documentar los resultados en la bitácora y en el reporte semanal correspondiente.

El desarrollo continuará priorizando el funcionamiento verificable del núcleo RAG sobre la incorporación de funcionalidades adicionales.

## Actualización — Cierre de Semana 2: infraestructura base AWS

### Decisiones tomadas

Se decidió alinear la implementación de AWS con el alcance formal de 10 semanas. Para la Semana 2 se limita el trabajo a infraestructura base mediante Terraform: VPC, subredes, tabla de rutas, IAM y S3. Se evita adelantar Aurora PostgreSQL/pgvector, Lambda, API Gateway u otros componentes correspondientes a semanas posteriores.

La infraestructura se implementa como Infrastructure as Code (IaC) con Terraform, con el objetivo de que pueda reproducirse mediante `terraform apply` y mantenerse sincronizada con el estado real de AWS.

La red se definió inicialmente con una VPC `10.0.0.0/16` y dos subredes privadas en `us-east-1a` y `us-east-1b`. No se creó todavía una subred pública, Internet Gateway ni NAT Gateway, ya que no son necesarios para el entregable de esta semana.

Para almacenamiento se definió un bucket S3 destinado a los documentos jurídicos. Se habilitaron bloqueo de acceso público, cifrado SSE-S3 mediante AES256 y versionado.

Para reducir la dependencia del usuario administrativo se creó el rol `TodoDerechoVecino-TerraformDeployRole`, con una política IAM específica para las operaciones requeridas por Terraform. Se mantiene temporalmente el usuario administrativo como acceso de respaldo mientras se continúa afinando el esquema de mínimo privilegio.

### Avances realizados

La infraestructura Terraform quedó desplegada correctamente en AWS.

Recursos principales:

* VPC: `vpc-0d72a23ee92829fb1`
* Subred privada A: `10.0.1.0/24` — `us-east-1a`
* Subred privada B: `10.0.2.0/24` — `us-east-1b`
* Tabla de rutas privada: `rtb-084cbe1af456f1c0e`
* Bucket S3: `todo-derecho-vecino-857385469837-us-east-1`
* Rol IAM: `TodoDerechoVecino-TerraformDeployRole`

El despliegue final mediante `terraform apply` terminó con:

`Apply complete! Resources: 8 added, 1 changed, 0 destroyed.`

Posteriormente se ejecutó `terraform plan` y Terraform confirmó:

`No changes. Your infrastructure matches the configuration.`

Por lo tanto, la infraestructura declarada en Terraform coincide actualmente con la infraestructura desplegada en AWS.

### Problemas y resolución

Durante el primer despliegue se identificaron permisos insuficientes en el rol de Terraform, específicamente para `ec2:DescribeVpcAttribute`. El permiso fue agregado a la política del rol y posteriormente se actualizó mediante Terraform.

El primer despliegue dejó parcialmente creados algunos recursos y Terraform marcó inicialmente la VPC y el bucket S3 como `tainted`. Se verificó directamente su estado en AWS, se confirmó que correspondían a la configuración prevista y se retiró el estado `tainted` mediante `terraform untaint`, evitando su reemplazo innecesario.

Después de corregir los permisos y el estado de Terraform, se ejecutó nuevamente el despliegue completo, que terminó correctamente.

### Git y control de versiones

El trabajo de infraestructura quedó incorporado a la rama `mvp-estancia`.

Commits relevantes:

* `0421b07` — `feat(terraform): add base network and S3 infrastructure`
* `ddd80ed` — `feat(terraform): semana 2 infrastructura como codigo`

El árbol de trabajo quedó limpio y los cambios fueron publicados en `origin/mvp-estancia`.

### Estado del proyecto

**Semana 2 completada y en tiempo.**

El entregable de infraestructura base definido para esta semana quedó implementado, desplegado y verificado.

La siguiente etapa corresponde a la **Semana 3: Base de datos y almacén vectorial**, cuyo objetivo será desplegar Aurora PostgreSQL Serverless v2 en modo Single-AZ con `pgvector` y diseñar el esquema para los documentos que serán ingeridos posteriormente.


## Semana 3 — Revisión del procesador y diseño de ingestión jurídica

### Estado al 2 de octubre de 2026

Se completó la validación inicial de Aurora PostgreSQL Serverless v2 y de la extensión `pgvector`. La base de datos se encuentra desplegada y accesible mediante un entorno de prueba privado utilizando una instancia EC2 y AWS Systems Manager Session Manager.

La extensión `vector` se encuentra instalada en versión 0.8.2 sobre PostgreSQL 16.15.

El esquema inicial de `legal_documents` y `legal_chunks` fue probado con datos ficticios. Se verificaron correctamente la relación documento/chunk, la clave foránea, eliminación en cascada, almacenamiento JSONB y restricción de unicidad. Los datos de prueba fueron eliminados posteriormente.

### Corpus definitivo del MVP

El corpus jurídico definitivo del MVP queda limitado a cinco documentos:

1. `PPCU_Hipodromo_reviewed.txt`
2. `PDDU-CUAUHTÉMOC_reviewed.txt`
3. `LEY_DE_ESTABLECIMIENTOS_MERCANTILES_PARA_LA_CDMX_5.4_reviewed.txt`
4. `LEY_DE_DESARROLLO_URBANO_DEL_DF_5.1_reviewed.txt`
5. `LEY_DE_CULTURA_CIVICA_DE_LA_CIUDAD_DE_MEXICO_2.8_reviewed.txt`

El Reglamento de la Ley de Establecimientos Mercantiles fue sustituido por la Ley correspondiente y no forma parte del corpus definitivo del MVP.

No se deben incorporar Reglamentos al corpus definitivo sin una decisión explícita posterior.

### Revisión de los JSON de chunks

Se revisaron:

* `leyes_cdmx/PPCU_Hipodromo_reviewed_chunks.json`
* `leyes_cdmx/PDDU-CUAUHTÉMOC_reviewed_chunks.json`
* `documentos_config.json`

Los JSON generados por el procesador ya contienen metadatos jurídicos relevantes, entre ellos:

`chunk_id`, `tipo_documento`, `titulo_completo`, `jurisdiccion`, `fecha_publicacion`, `fecha_ultima_reforma`, `estado_vigencia`, `titulo`, `capitulo`, `seccion`, `articulo`, `fraccion`, `contexto_superior`, `tema_principal`, `tipo_disposicion`, `sujetos_obligados`, `cita_legal`, `fuente`, `texto` y `needs_review`.

Estos metadatos deben aprovecharse durante la ingestión en Aurora y no debe crearse un segundo sistema paralelo de procesamiento jurídico.

### Problema detectado en PDDU

El archivo:

`PDDU-CUAUHTÉMOC_reviewed_chunks.json`

contiene 13 chunks.

Sin embargo, el primer chunk presenta incorrectamente:

`"titulo_completo": "Programa Parcial de Desarrollo Urbano Hipódromo"`

aunque corresponde al:

`Programa Delegacional de Desarrollo Urbano de Cuauhtémoc`.

También presenta una cita legal asociada incorrectamente al PPCU.

Este problema confirma que los metadatos del PDDU deben corregirse en el proceso de generación y no mediante edición manual del JSON resultante.

La siguiente acción será revisar `legal_document_processor.py` para identificar el origen del error.

### Hallazgo sobre tablas y cuadros normativos

Se comprobó que las estructuras normativas especiales de los programas urbanos están llegando a los JSON, pero actualmente permanecen embebidas dentro del campo `texto` de los chunks.

En PPCU se localizaron referencias a:

* `Tabla 20`
* `Normatividad por vialidad`

En PDDU se localizaron referencias a:

* `Cuadro 15`
* `Cuadro 16`
* `Tabla de Usos del Suelo`
* `Normas de Ordenación sobre Vialidad`

Estas estructuras todavía no se representan como tablas estructuradas.

### Decisión arquitectónica provisional

No se sustituirá `legal_chunks`.

Se propone una segunda etapa de procesamiento que trabaje sobre los chunks existentes:

```text
Documento revisado
        |
        v
legal_document_processor.py
        |
        v
Chunks JSON
        |
        +----> legal_chunks
        |
        +----> extracción de estructuras normativas
                         |
                         v
                    legal_tables
                         |
                         v
                  legal_table_rows
```

El objetivo es conservar simultáneamente:

* el texto original;
* su contexto;
* los metadatos jurídicos;
* la procedencia;
* y una representación estructurada de las tablas/cuadros normativos.

Esto permitirá que el agente utilice extracción estructurada para preguntas exactas y recuperación semántica/contextual para preguntas jurídicas más complejas.

### Tablas prioritarias para validación

La primera tabla piloto será la **Tabla 20 del PPCU Hipódromo: “Normatividad por vialidad”**.

La tabla contiene, entre otras, las columnas:

* Calle
* Tramo
* Zona
* Intensidad
* Usos permitidos

Debe conservarse la condición de aplicabilidad según la cual la zonificación corresponde a los predios con frente a la vialidad indicada.

Debe conservarse también el valor original de la intensidad, ya que no todos los registros tienen la misma estructura.

La referencia `Usos permitidos → Tabla de compatibilidad` no debe convertirse en usos concretos mediante inferencia.

Posteriormente se validarán:

* Cuadro 15 del PDDU: “Tabla de Usos del Suelo en Suelo Urbano”.
* Cuadro 16 del PDDU: “Normas de Ordenación sobre Vialidad”.

### Regla conceptual

La prioridad del MVP es la interpretación jurídica con contexto y procedencia, no únicamente la extracción de texto.

Por ello, las estructuras normativas deben conservar:

* contexto;
* aplicabilidad;
* excepciones;
* notas;
* condiciones;
* referencias cruzadas;
* procedencia documental.

No se deben inferir permisos, prohibiciones o condiciones que no estén explícitamente sustentados en el documento fuente.

### Estado de las tablas Aurora

Todavía NO se han creado:

* `legal_tables`
* `legal_table_rows`
* `legal_embeddings`

No se debe crear `legal_embeddings` hasta definir el modelo de embeddings y su dimensión.

### Próximo paso

Antes de modificar Aurora o crear nuevas tablas:

1. revisar `legal_document_processor.py`;
2. identificar cómo se construyen los metadatos documentales;
3. explicar y corregir el error de metadatos del PDDU;
4. revisar el tratamiento especial que reciben PDDU y PPCU;
5. regenerar y validar sus JSON;
6. diseñar la extracción estructurada de tablas/cuadros;
7. probar primero con la Tabla 20 del PPCU;
8. validar posteriormente Cuadro 15 y Cuadro 16;
9. sólo después incorporar las estructuras validadas a Aurora.

**No modificar infraestructura ni esquema de Aurora hasta completar esta validación.**
