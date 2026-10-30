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

# Bitácora — Todo Derecho Vecino

## Semana 3 — Segunda parte

### Base de datos, acceso, validación, versionamiento y cierre de evidencia

**Rama:** `mvp-estancia`
**Periodo:** 30 de septiembre – 3 de octubre de 2026

---

## 1. Contexto

Esta bitácora corresponde a la **segunda parte de la Semana 3** de desarrollo de Todo Derecho Vecino.

La primera parte de la semana estuvo orientada principalmente a la preparación y despliegue de la infraestructura de base de datos mediante Terraform, así como a la actualización y validación del corpus jurídico MVP.

En esta segunda parte se cerró la validación de la base de datos, se recuperaron las credenciales necesarias para acceder a Aurora, se estableció nuevamente el acceso mediante AWS Systems Manager, se verificó el esquema directamente con `psql`, se documentó la ausencia de datos de prueba y finalmente se versionaron y publicaron los cambios de infraestructura en GitHub.

El objetivo de Semana 3, de acuerdo con el alcance del proyecto, es disponer de **Aurora PostgreSQL Serverless v2 en modo Single-AZ con `pgvector` y un esquema de datos diseñado para los documentos que serán ingeridos**, dejando una base accesible desde el entorno de prueba.

---

# 2. Actividades realizadas

## 2.1. Recuperación de las credenciales de Aurora

Al intentar continuar con las pruebas de `psql`, se identificó que no se tenía disponible la contraseña del usuario administrativo de PostgreSQL.

Se revisó la configuración de Aurora y se confirmó que el recurso fue definido mediante Terraform utilizando:

```text
manage_master_user_password = true
```

Por lo tanto, la contraseña no se encontraba escrita en `aurora.tf`, sino que AWS la administra mediante **AWS Secrets Manager**.

Se obtuvo primero el ARN del secreto asociado al cluster:

```text
arn:aws:secretsmanager:us-east-1:857385469837:secret:rds!cluster-4c3fc386-d1da-4de9-ade5-3849f8b22f21-Tfw3dM
```

Posteriormente se recuperó el contenido del secreto mediante AWS CLI.

La contraseña se utilizó únicamente para establecer la conexión de prueba y **no se incorporó al repositorio ni a los archivos de Terraform**.

**Estado: RESUELTO.**

---

## 2.2. Reactivación de la sesión de acceso mediante SSM

Se detectó que la sesión de AWS Systems Manager necesaria para acceder a Aurora no se encontraba activa.

Se restableció el port forwarding mediante:

```bash
aws ssm start-session \
  --target i-04a1bd28964bbf829 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["todo-derecho-vecino-aurora.cluster-cmh6wme8kwix.us-east-1.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["5432"]}'
```

Esto permitió establecer desde el equipo local una conexión a PostgreSQL a través del puerto local `5432`.

Posteriormente se utilizó:

```bash
psql -h localhost -p 5432 -U tdv_admin -d tododerechovecino
```

La conexión fue exitosa.

**Estado: RESUELTO.**

---

# 3. Validación de la base de datos

Una vez dentro de `psql`, se realizaron consultas exclusivamente de lectura para obtener evidencia del estado real de Aurora.

## 3.1. Base de datos y usuario

Se confirmó:

```text
current_database
-------------------
tododerechovecino
```

y:

```text
current_user
--------------
tdv_admin
```

## 3.2. Versión de PostgreSQL

La instancia reportó:

```text
PostgreSQL 16.15 on aarch64-linux, compiled by gcc-10.5.0, 64-bit
```

## 3.3. Extensión pgvector

Se verificó:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

Resultado:

```text
extname | extversion
---------+-----------
vector  | 0.8.2
```

Con esto quedó comprobado que la extensión requerida para el almacén vectorial se encuentra instalada.

**Estado: RESUELTO.**

---

# 4. Validación del esquema

La consulta:

```text
\dt
```

confirmó la existencia de:

```text
public | legal_chunks
public | legal_documents
```

Posteriormente se inspeccionó la estructura de ambas tablas.

## 4.1. `legal_documents`

La tabla contiene campos para:

* identificación del documento;
* nombre;
* tipo documental;
* autoridad;
* fuente;
* fecha de publicación;
* fecha de reforma;
* versión;
* referencia al objeto almacenado en S3;
* hash del documento;
* fechas de creación y actualización.

## 4.2. `legal_chunks`

La tabla contiene campos para:

* identificación del fragmento;
* documento al que pertenece;
* índice del fragmento;
* título;
* capítulo;
* sección;
* artículo;
* fracción;
* cita legal;
* texto;
* metadatos `JSONB`;
* fecha de creación.

## 4.3. Relación entre documentos y fragmentos

Se confirmó la existencia de la relación:

```text
legal_chunks.document_id
        ↓
legal_documents.id
```

mediante una llave foránea con:

```text
ON DELETE CASCADE
```

También se confirmó la restricción:

```text
UNIQUE (document_id, chunk_index)
```

Esto evita que un mismo documento tenga dos fragmentos con el mismo índice.

**Estado: RESUELTO.**

---

# 5. Comprobación de datos de prueba

Durante la construcción del esquema se habían utilizado datos ficticios para probar las relaciones y restricciones de la base.

Antes de cerrar la Semana 3 se verificó que esos datos hubieran sido eliminados.

Se ejecutó:

```sql
SELECT
    (SELECT COUNT(*) FROM legal_documents) AS documentos,
    (SELECT COUNT(*) FROM legal_chunks) AS fragmentos;
```

Resultado:

```text
documentos | fragmentos
-----------+-----------
0          | 0
```

Por lo tanto, la base queda preparada para recibir posteriormente los datos reales del corpus jurídico.

**Estado: RESUELTO.**

---

# 6. Validación de Terraform

Después del despliegue se ejecutó:

```bash
terraform plan
```

Terraform respondió:

```text
No changes. Your infrastructure matches the configuration.
```

Esto confirmó que no había diferencias pendientes entre la infraestructura declarada y los recursos desplegados.

La infraestructura de esta etapa quedó incorporada al repositorio mediante:

```text
terraform/access.tf
terraform/aurora.tf
terraform/plan-semana3.txt
```

**Estado: RESUELTO.**

---

# 7. Versionamiento y publicación en GitHub

Al intentar publicar los cambios mediante:

```bash
git push origin mvp-estancia
```

Git rechazó inicialmente la operación porque GitHub contenía un commit que no se encontraba en la copia local.

Se ejecutó:

```bash
git fetch origin
```

y se comprobó que el cambio remoto correspondía únicamente a:

```text
f2da9fe Revise README description for clarity on legal tool
```

El cambio afectaba solamente:

```text
README.md
```

Para evitar sobrescribir trabajo remoto se utilizó:

```bash
git pull --rebase origin mvp-estancia
```

El rebase integró correctamente el cambio remoto y reaplicó los tres commits locales de esta etapa.

Posteriormente se realizó nuevamente:

```bash
git push origin mvp-estancia
```

El envío terminó correctamente:

```text
f2da9fe..38284e3  mvp-estancia -> mvp-estancia
```

La rama `mvp-estancia` quedó publicada y sincronizada con GitHub.

El commit principal de infraestructura de Semana 3 quedó como:

```text
38284e3 feat(terraform): semana 3 infraestructura de base de datos
```

**Estado: RESUELTO.**

---

# 8. Estado de los temas principales

| Tema                                          | Estado                                  |
| --------------------------------------------- | --------------------------------------- |
| Aurora PostgreSQL Serverless v2               | ✅ Resuelto                              |
| Configuración Single-AZ                       | ✅ Resuelto                              |
| PostgreSQL 16.15                              | ✅ Verificado                            |
| `pgvector`                                    | ✅ Instalado y verificado, versión 0.8.2 |
| Base `tododerechovecino`                      | ✅ Verificada                            |
| Usuario `tdv_admin`                           | ✅ Verificado                            |
| Recuperación de contraseña                    | ✅ Resuelto mediante Secrets Manager     |
| Acceso mediante SSM                           | ✅ Resuelto                              |
| Conexión mediante `psql`                      | ✅ Verificada                            |
| Tabla `legal_documents`                       | ✅ Creada y verificada                   |
| Tabla `legal_chunks`                          | ✅ Creada y verificada                   |
| Relación documento → fragmentos               | ✅ Verificada                            |
| Restricción de índices de fragmentos          | ✅ Verificada                            |
| Datos ficticios residuales                    | ✅ Eliminados                            |
| Terraform                                     | ✅ Validado sin cambios pendientes       |
| Infraestructura versionada                    | ✅                                       |
| GitHub actualizado                            | ✅                                       |
| Corpus jurídico MVP actualizado a versión 2.9 | ✅                                       |
| Ingesta real del corpus                       | ⏳ Pendiente, corresponde a Semana 4     |
| Generación de embeddings                      | ⏳ Pendiente, corresponde a Semana 4     |
| Carga de embeddings en `pgvector`             | ⏳ Pendiente, corresponde a Semana 4     |
| Consultas de similitud                        | ⏳ Pendiente, corresponde a Semana 4     |
| Evaluación del retriever                      | ⏳ Pendiente, corresponde a Semana 5     |

---

# 9. Pendientes que se dejan abiertos

Los siguientes asuntos quedan deliberadamente pendientes y **no se consideran fallas de la Semana 3**.

## 9.1. Ingesta del corpus jurídico

La base está preparada, pero todavía no se ha realizado la carga definitiva de los 1,235 fragmentos del corpus MVP.

Esto corresponde a la Semana 4.

## 9.2. Generación de embeddings

Todavía no se ha realizado la vectorización definitiva del corpus.

También corresponde a la Semana 4.

## 9.3. Pruebas de similitud vectorial

La extensión `pgvector` está instalada, pero todavía no se ha realizado la prueba completa de recuperación semántica sobre el corpus real.

Queda para la siguiente etapa de desarrollo.

## 9.4. Evaluación formal del retriever

La evaluación mediante preguntas de prueba, criterio de corrección y métrica corresponde a la Semana 5.

No debe adelantarse como requisito de cierre de Semana 3.

---

# 10. Pendiente especial: control de costos de AWS

Durante esta segunda parte surgió una necesidad operativa importante: **evitar que los recursos de AWS permanezcan generando cargos cuando no se esté trabajando activamente en el proyecto**.

Este tema se identificó, pero deliberadamente **no se modificó todavía la infraestructura de Semana 3** para resolverlo.

La razón es mantener separado el entregable de la semana de una estrategia posterior de operación y ahorro.

Queda pendiente diseñar y documentar un procedimiento seguro que permita:

1. trabajar con los recursos de AWS cuando sean necesarios;
2. detener o eliminar los recursos que generen cargos cuando no se utilicen;
3. conservar los datos necesarios para poder continuar posteriormente;
4. evitar borrar accidentalmente infraestructura o información requerida por el proyecto;
5. definir qué recursos pueden detenerse, cuáles deben conservarse y cuáles conviene recrear mediante Terraform;
6. determinar qué componentes pueden continuar generando costos aunque una parte de la infraestructura se encuentre detenida.

Este punto será tratado **después de cerrar formalmente el reporte de Semana 3**, como una actividad adicional de operación y control de costos.

**Estado: PENDIENTE.**

---

# 11. Pendientes operativos para continuar el proyecto

Al retomar el proyecto, la secuencia prevista es:

### Primero

Cerrar y entregar el reporte de Semana 3.

### Después

Resolver la estrategia de operación de AWS para evitar cargos innecesarios durante los periodos en que no se trabaje en el proyecto.

### Posteriormente

Iniciar la Semana 4:

**Ingesta y vectorización del corpus jurídico.**

El objetivo será cargar el corpus seleccionado, generar sus embeddings e incorporarlos a `pgvector`, dejando funcionando consultas de similitud en las pruebas correspondientes.

---

# 12. Estado de cierre de esta segunda parte

La segunda parte de la Semana 3 queda **cerrada técnicamente**.

La infraestructura está desplegada, la base de datos es accesible, PostgreSQL y `pgvector` fueron verificados, el esquema fue inspeccionado directamente mediante `psql`, los datos de prueba fueron eliminados, Terraform no presenta cambios pendientes y los commits fueron publicados correctamente en GitHub.

Lo que queda pendiente ya no corresponde a problemas abiertos de la infraestructura de Semana 3, sino a:

* la preparación del reporte formal;
* el control operativo de costos de AWS;
* y las actividades de ingesta y vectorización correspondientes a la Semana 4.

La infraestructura queda, por tanto, en condiciones de ser utilizada como base para la siguiente etapa del proyecto.

## Cierre operativo de la infraestructura DEV — Semana 3

### Decisión de arquitectura

Durante la semana 3 se completó la separación de la infraestructura Terraform en dos ambientes con responsabilidades diferentes:

* `terraform/base`: infraestructura persistente.
* `terraform/dev`: infraestructura efímera para desarrollo y pruebas.

La separación se realizó para que el ambiente de desarrollo pueda destruirse completamente cuando no se esté utilizando, sin afectar los recursos que deben permanecer disponibles, principalmente el almacenamiento S3 de los documentos jurídicos y el rol IAM utilizado para despliegues.

La decisión es consistente con el alcance del proyecto, que establece que la infraestructura utilizada debe quedar definida en Terraform y que el sistema debe poder reconstruirse a partir del código.

### Migración del estado Terraform

Antes de modificar el estado se realizaron respaldos del estado original.

Posteriormente se migraron los recursos correspondientes a los estados independientes de `terraform/base` y `terraform/dev`.

Después de la migración se verificó que:

```text
terraform/base plan → No changes
terraform/dev plan  → No changes
```

El estado Terraform de la raíz quedó vacío, mientras que los recursos fueron administrados desde sus respectivos directorios.

### Protección de infraestructura persistente

Se agregó `prevent_destroy = true` al bucket S3 de documentos jurídicos y al rol IAM de despliegue.

La intención es evitar que una operación destinada al ambiente DEV pueda destruir accidentalmente infraestructura persistente.

El bucket S3 se mantiene como almacenamiento de los documentos fuente del corpus jurídico. Aurora no debe considerarse el almacenamiento permanente de esos documentos.

### Validación del ciclo de vida DEV

Se implementaron scripts operativos para controlar el ambiente:

```text
./terraform/dev-up.sh
./terraform/dev-status.sh
./terraform/dev-down.sh
```

Se ejecutó el ciclo completo de operación.

Primero se destruyó el ambiente DEV y se verificó la eliminación de sus recursos. Posteriormente se reconstruyó desde Terraform y se verificó nuevamente su funcionamiento.

La reconstrucción creó nuevamente:

* Aurora PostgreSQL Serverless v2;
* instancia Aurora;
* VPC y subredes privadas;
* Security Groups;
* EC2 temporal `admin_test`;
* roles e instance profile necesarios para administración;
* VPC endpoints de Systems Manager.

Después de las pruebas se volvió a ejecutar `dev-down`.

En la última ejecución se destruyeron los 20 recursos administrados por `terraform/dev`.

Posteriormente se verificó:

```text
terraform/base plan → No changes
```

Esto confirmó que la destrucción completa de DEV no afecta la infraestructura persistente.

### Pruebas de Aurora

La instancia reconstruida utilizó:

```text
Aurora PostgreSQL Serverless v2
PostgreSQL 16.15
Single-AZ
min_capacity = 0.5 ACU
max_capacity = 2 ACU
Puerto = 5432
Acceso público = No
Cifrado = Habilitado
```

Se verificó el acceso mediante una instancia EC2 temporal y AWS Systems Manager.

La conectividad TCP desde `admin_test` hacia Aurora fue comprobada satisfactoriamente.

Posteriormente se estableció un túnel SSM desde el equipo local y se realizó una conexión mediante `psql`.

Se verificó:

* nombre de la base de datos;
* usuario actual;
* versión de PostgreSQL;
* conectividad con Aurora.

### Gestión de credenciales

Se confirmó que Aurora utiliza:

```hcl
manage_master_user_password = true
```

Por lo tanto, la contraseña maestra no se almacena directamente en Terraform.

AWS Secrets Manager administra la credencial de Aurora.

No fue necesario modificar Terraform para permitir la reconstrucción del ambiente. La intervención manual solamente es necesaria cuando se requiere acceder administrativamente a PostgreSQL.

Esto establece una distinción importante entre:

```text
Reconstrucción de infraestructura
        ↓
Automatizada mediante Terraform

Acceso administrativo a PostgreSQL
        ↓
Requiere recuperar el secreto vigente de AWS Secrets Manager
```

Después de destruir y reconstruir Aurora no debe suponerse que una contraseña utilizada anteriormente continúa vigente.

### Verificación de pgvector

Después de la reconstrucción de Aurora se creó la extensión PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

La extensión quedó verificada con versión:

```text
vector | 0.8.2
```

La base de datos todavía no contiene el esquema definitivo ni las tablas del corpus, por lo que `\dt` no mostró relaciones.

Esto se considera normal en esta etapa.

La inicialización del esquema, chunking, embeddings y carga del corpus quedan como trabajo posterior de la etapa de ingesta y vectorización.

### Problema identificado y solución

El principal problema operativo detectado fue que Aurora, al ser parte de la infraestructura efímera, pierde su estado de base de datos al ser destruida.

La solución arquitectónica adoptada es no depender de Aurora como repositorio permanente de los documentos fuente.

La estrategia será:

```text
S3
 ↓
documentos jurídicos fuente
 ↓
chunking
 ↓
embeddings
 ↓
Aurora + pgvector
```

De esta forma, Aurora puede reconstruirse y posteriormente volver a poblarse a partir del corpus almacenado en S3.

### Resultado

Se considera validada la separación entre infraestructura persistente y efímera.

El ambiente DEV puede:

```text
crear → probar → destruir → reconstruir
```

sin afectar los recursos persistentes de BASE.

El ambiente queda apagado al finalizar esta etapa para evitar mantener recursos AWS innecesarios mientras no se desarrolla.

### Estado frente al cronograma

La infraestructura correspondiente a la semana 3 quedó desplegable y accesible desde el entorno de prueba, incluyendo Aurora PostgreSQL Serverless v2 y pgvector.

La infraestructura puede reconstruirse desde Terraform.

Queda pendiente para la siguiente etapa:

* definición/implementación del esquema de datos;
* extracción y chunking del corpus;
* generación de embeddings;
* carga de documentos en pgvector;
* pruebas de consultas de similitud.

Esto corresponde al objetivo de ingesta y vectorización previsto para la siguiente etapa del cronograma.

## Actualización de seguimiento — 12 de octubre de 2026

### Preparación local del cargador de embeddings

Esta actualización registra los avances posteriores a la preparación del esquema. El usuario confirma que DEV fue verificado y que Aurora se apagó nuevamente al terminar; por tanto, el estado operativo actual es DEV apagado intencionalmente. No se encendió AWS ni se escribieron datos en Aurora durante esta sesión.

#### Trabajo realizado y archivos

- Se añadió `scripts/load_embeddings.py`, cuyo propósito es validar e ingerir en Aurora los documentos, los chunks existentes y los embeddings ya generados. No vuelve a generar vectores ni introduce otro proceso de chunking.
- El cargador identifica documentos mediante la ruta del JSON de chunks y vincula cada embedding usando el archivo fuente, `chunk_id` y la posición determinista del chunk. Conserva los metadatos jurídicos y `needs_review`.
- Antes de cualquier conexión valida que cada embedding corresponda a un segmento del corpus configurado, que el texto coincida con el segmento, que el modelo sea `amazon.titan-embed-text-v2:0`, que existan 1024 valores numéricos finitos y que no haya registros duplicados.
- Por defecto el cargador solo valida y muestra conteos. Para ejecutar escrituras exige `--apply`; usa `psql`, `PGPASSFILE`/`.pgpass` con permisos restringidos y no acepta contraseñas como argumentos.
- El modo piloto se habilita explícitamente con `--allow-incomplete`; es incremental, no elimina embeddings existentes y aborta si detecta que el corpus fuente ya cargado tiene contenido distinto. La carga completa rechaza segmentos faltantes y sincroniza chunks/embeddings de los documentos incluidos en la configuración, dentro de una transacción.
- Se actualizó `README.md` con los comandos para validar/cargar el piloto y generar, validar y cargar el JSONL completo. También recuerda que los datos de Aurora DEV se pierden al destruir el entorno y que deben conservarse los artefactos fuente.
- Se generó `salida/embeddings_piloto_25bc7c1d8a1e.jsonl`, artefacto local ignorado por Git, con un embedding del chunk `25bc7c1d8a1e` (Ley de Desarrollo Urbano, artículo 12). Su propósito es probar el formato y el camino de ingesta con un solo segmento sin generar el corpus completo.

#### Validaciones locales

- El `dry-run` de `generar_embeddings_persistente.py --limit 0 --dry-run` encontró los cinco documentos configurados, 1,235 chunks y 1,369 segmentos estimados; no llamó a Bedrock ni creó vectores.
- El piloto generó correctamente un vector de 1024 dimensiones. El cargador lo validó localmente con `--allow-incomplete`: encontró 1 embedding y 1,368 segmentos todavía faltantes. Sin `--allow-incomplete`, rechazó el archivo parcial, como medida para impedir una carga piloto accidental como carga completa.
- El cargador no se conectó a PostgreSQL, no ejecutó `--apply` y no modificó Aurora. `problems` no reportó errores en `scripts/load_embeddings.py` y `git diff --check` pasó.
- Se confirmó que los 1,235 chunks actuales están marcados `needs_review=true`. El procesador usa esa marca para metadatos inferidos que requieren confirmación humana; por decisión del usuario se conservarán las marcas y se incluirán los registros durante esta etapa, no se filtrarán automáticamente.
- Existen dos vectores locales anteriores con modelo/dimensión correctos, pero corresponden a chunks de solo 10 caracteres; no se usarán como evidencia de una prueba semántica útil. Se mantuvieron sin cambios.

#### Pendiente — secuencia para completar la prueba de similitud

1. Mantener Aurora apagada mientras se termina de preparar el JSONL completo con `generar_embeddings_persistente.py --limit 0 --output salida/embeddings_mvp_completos.jsonl`; revisar el resultado antes de cargarlo. El corpus completo requiere hasta 1,369 llamadas de generación; el piloto ya realizado fue una llamada adicional independiente.
2. Validar el archivo completo con `scripts/load_embeddings.py` sin `--allow-incomplete` y sin `--apply`; exigir cero segmentos faltantes.
3. Cuando el usuario decida trabajar en AWS, encender DEV mediante `terraform/dev-up.sh`, revisar el plan y confirmar la conectividad. El usuario informa que el esquema fue creado/verificado previamente; como DEV se apagó después, volver a comprobar el esquema tras el próximo encendido, aplicándolo con el inicializador solo si hace falta.
4. Abrir el túnel SSM y cargar primero el piloto con `--allow-incomplete --apply`; revisar los conteos y el resultado de una consulta de cercanía antes de iniciar una carga completa.
5. Para la carga completa, ejecutar el cargador sobre `embeddings_mvp_completos.jsonl` sin `--allow-incomplete` y con `--apply`; registrar conteos de documentos, chunks y segmentos. La prueba de similitud debe usar un embedding de consulta generado por el mismo modelo y dimensión, y mostrar resultados con citas legales.
6. Antes de apagar DEV, conservar el JSONL completo y registrar evidencia sin secretos. El cargador se preparó localmente; la escritura real y la búsqueda vectorial continúan pendientes.

## Actualización de seguimiento — 10 de octubre de 2026
### Esquema SQL, inicializador y preparación de la prueba de despliegue 
Esta nota distingue los cambios locales de las pruebas que siguen pendientes. Al cierre de esta actualización, Aurora no existe porque `terraform/dev` está apagado intencionalmente; este estado es esperado y no debe registrarse como fallo de infraestructura. ### Trabajo realizado - Se definió `sql/001_initial_schema.sql` con `legal_documents`, `legal_chunks` y `legal_embeddings`. - Se conserva `legal_chunks` como tabla de fragmentos del procesador existente; no se crea un sistema paralelo de chunking. - `legal_embeddings` relaciona embedding, chunk y documento mediante una clave foránea compuesta; `embedding` se define como `VECTOR(1024)`. - Se conserva `UNIQUE(document_id, chunk_index)` y `UNIQUE(legal_chunk_id, segment_index)`. No se presupone que `chunk_id` sea único por documento. - Se añadieron índices B-tree/GIN para consulta de documento y metadatos. HNSW queda pospuesto hasta después de la carga y de evaluar recursos en Aurora Serverless v2 con máximo configurado de 2 ACU. - Se preparó `scripts/init_db.sh` para consultar Aurora, obtener `admin_test_instance_id` desde Terraform, comprobar SSM, recuperar credenciales desde Secrets Manager, abrir túnel privado, ejecutar SQL y verificar extensión/tablas/tipo vectorial. - `bash -n scripts/init_db.sh` pasó; `git diff --check` no reportó errores; el archivo tiene permisos `700`. - El paso de contraseña a Python se cambió para evitar incluirla en los argumentos del proceso. Sigue siendo información sensible: no imprimirla ni guardarla en Git. - Los outputs necesarios ya están declarados en `terraform/dev/aurora.tf`: `aurora_cluster_endpoint`, `aurora_reader_endpoint`, `aurora_port`, `aurora_database_name`, `admin_test_instance_id` y `vpc_id`. No crear un `outputs.tf` duplicado. - Se inspeccionó `terraform/dev-up.sh`: `init`, `plan`, solicitud explícita de `APPLY`, `apply -auto-approve` y outputs. No se ejecutó en esta actualización. ### Decisiones vigentes 1. `terraform/base` es persistente; `terraform/dev` es efímero. No destruir ni modificar `base` durante pruebas de DEV. 2. Aurora puede estar destruido cuando DEV está apagado. Es un estado intencional y no un incidente por sí mismo. 3. S3 es la fuente persistente para reconstruir documentos y artefactos; los datos dentro de Aurora se pierden al destruir DEV. 4. La inicialización del esquema no equivale a ingesta: no carga ni regenera documentos, chunks o embeddings. 5. Modelo de embeddings acordado: `amazon.titan-embed-text-v2:0`, 1024 dimensiones. Los artefactos existentes en S3 no deben regenerarse para resolver problemas de esquema. 6. La ingesta y consultas de similitud corresponden a Semana 4; evaluación del retriever a Semana 5. 7. PPCU Tabla 20 y PDDU Cuadros 15/16 requieren revisión separada. No agregar aún `legal_tables`. ### Estado: comprobado y pendiente **Comprobado localmente:** el SQL existe; el inicializador existe y es ejecutable; `bash -n` y `git diff --check` pasan; los outputs de Terraform están declarados. **Pendiente de prueba real:** DEV sigue apagado intencionalmente y Aurora no existe al cierre de esta actualización; no se ejecutó el encendido de prueba; no se ejecutó el SQL en una instancia nueva; no se reconfirmó `vector` tras reconstrucción; no se probó el túnel SSM + `psql`; no se cargaron los 1,235 chunks ni los 1,369 segmentos; no se ejecutó búsqueda semántica; no se hizo commit ni push de los archivos locales nuevos. ### Matriz de fuentes de fallo | Punto | Posible fallo | Respuesta de diagnóstico | |---|---|---| | Git | Rama equivocada o cambios no identificados | Revisar rama y `git status`; no hacer `git add .` automáticamente | | Terraform | Estado ausente, obsoleto o de otro backend/workspace | Confirmar directorio/workspace/backend y outputs; nunca editar JSON de state manualmente | | Plan | Cambios inesperados o afectación a `base` | No escribir `APPLY`; revisar recursos y acciones del plan | | Aurora | Cluster ausente o no `available` | Diferenciar DEV apagado de fallo de despliegue; revisar estado y outputs | | Secrets Manager | `MasterUserSecret` ausente o permisos insuficientes | Revisar configuración/IAM sin mostrar el secreto | | SSM | Instancia no `Online` | Revisar perfil IAM, SSM Agent, endpoints, DNS, rutas y SG | | Red | EC2 no alcanza Aurora por TCP 5432 | Revisar rutas privadas y regla de entrada entre SGs | | Herramientas | Falta AWS CLI, Terraform, `psql`, `pg_isready`, Python o plugin SSM | Validar dependencias antes de abrir túnel | | Túnel | Puerto 15432 ocupado o sesión termina | Identificar proceso y revisar `/tmp/tdv-init-db-ssm.log` | | pgvector | Extensión no disponible/autorizada tras reconstrucción | Verificar compatibilidad con la versión desplegada; no asumir resultados históricos | | SQL | Tablas previas incompatibles | `IF NOT EXISTS` no migra; inspeccionar catálogo antes de modificar/borrar | | Embeddings | Modelo o dimensión no coincide | Confirmar modelo, 1024 dimensiones y correspondencia segmento/chunk/documento | | Credenciales | Secretos expuestos en terminal/logs | No imprimir valores sensibles ni compartir `SecretString` | | Costos | DEV queda encendido | Registrar encendido/apagado y comprobar estado final | | Git | Se incluyen scripts temporales o archivos sensibles | Revisar `.gitignore` y los dos scripts de generación antes de stage/commit | ### Pendientes inmediatos 1. Revisar el diff de `.gitignore`. 2. Inspeccionar `generar_embeddings.py` y `generar_embeddings_persistente.py` antes de decidir si se versionan. 3. Revisar archivos de `sql/` y `scripts/`; no hacer commit/push todavía. 4. Preparar y ejecutar la prueba controlada solo después de revisar el plan y recibir autorización explícita. 5. Registrar outputs, estado de Aurora/SSM, versión de `vector`, tablas y tipo `vector(1024)`. 6. Decidir el apagado de DEV con autorización y confirmar que `terraform/base` permanece intacto. 7. Revisar las tablas normativas especiales antes de cerrar la preparación de ingesta. ### Evaluación del cronograma El diseño y la preparación local están avanzados, pero la Semana 3 no se considera completada por validar la sintaxis únicamente. Se requiere una prueba real de base desplegada y accesible con `pgvector` y esquema verificados. La ingesta permanece en Semana 4. 

## Semana 4. Ingesta, vectorización y consultas de similitud

**Fecha de cierre:** 16 de octubre de 2026
**Estado:** Entregable técnico de la semana completado.

### Objetivo

Cargar el corpus jurídico preparado en Aurora PostgreSQL con pgvector y comprobar que se pueden recuperar fragmentos mediante consultas de similitud ejecutadas desde el entorno local.

### Trabajo realizado

- Se validó el conjunto de cinco instrumentos jurídicos del MVP.
- Se validaron 1,235 chunks fuente y 1,369 segmentos de embeddings.
- Se comprobó que no faltaban segmentos esperados en el archivo de embeddings.
- Se inicializó el esquema de la base de datos: `legal_documents`, `legal_chunks` y `legal_embeddings`.
- Se cargaron los cinco documentos, los 1,235 chunks y los 1,369 embeddings en Aurora PostgreSQL.
- Se verificó que todos los vectores tienen 1,024 dimensiones.
- Se comprobó que los 1,369 registros de embeddings y los 1,235 chunks conservan `needs_review = true`.
- Se ejecutaron consultas de similitud desde el entorno local, generando el vector de la pregunta con `amazon.titan-embed-text-v2:0` y consultando Aurora a través de un túnel privado de AWS Systems Manager (SSM).

### Resultados de las pruebas

La búsqueda independiente sobre el Programa Parcial de Desarrollo Urbano de la colonia Hipódromo recuperó, entre otros resultados, la sección 29.90, relacionada con condiciones de convivencia y permisos provisionales para ocupar la vía pública, y la sección 6.3, con antecedentes del desarrollo urbano de la colonia.

La búsqueda independiente sobre la Ley de Establecimientos Mercantiles para la Ciudad de México recuperó disposiciones vinculadas con:

- Artículo 10, fracción XV: ruido al exterior que afecte los derechos de terceros.
- Artículo 30: límites de emisiones sonoras dentro de los establecimientos.
- Artículo 10, fracción IX: exhibición del horario de servicio y otra información.
- Artículo 15: restricciones para la colocación de enseres en determinados espacios.
- Artículo 29: prohibición de la modalidad de barra libre y promociones similares.

Los resultados muestran que pgvector ordena fragmentos por similitud semántica. Sin embargo, la cercanía vectorial no demuestra por sí sola la pertinencia jurídica ni la aplicabilidad de una disposición a un predio o establecimiento concreto. La consulta amplia sobre uso de suelo, horarios, ruido y molestias vecinales tampoco garantizó que aparecieran resultados de todos los instrumentos solicitados en una sola lista.

### Estado de los datos

| Elemento | Resultado |
|---|---:|
| Instrumentos cargados | 5 |
| Chunks fuente | 1,235 |
| Segmentos de embeddings | 1,369 |
| Dimensión mínima y máxima de los vectores | 1,024 |
| Embeddings pendientes de revisión jurídica | 1,369 |
| Chunks pendientes de revisión jurídica | 1,235 |

### Limitaciones conocidas

- La carga realizada se alimentó desde el archivo local `salida/embeddings_mvp.jsonl`. Aunque los artefactos también están almacenados en S3, el cargador utilizado no implementa todavía una ingesta directa desde S3.
- Las consultas ejecutadas fueron pruebas técnicas de similitud; todavía no existe un retriever evaluado formalmente con un conjunto fijo de preguntas.
- No se ha calculado precisión, recall ni una calificación manual de recuperación correcta.
- Los resultados jurídicos siguen pendientes de revisión; no se modificó el indicador `needs_review`.
- No se modificó el modelo de embeddings ni se regeneraron los vectores.

### Criterio de cierre

Se considera cumplido el entregable de la Semana 4: el corpus está cargado e indexado en Aurora PostgreSQL con pgvector y se verificaron consultas de similitud desde el entorno local.

Este cierre acredita el funcionamiento técnico inicial de la búsqueda vectorial, no la calidad jurídica definitiva de las respuestas.

### Siguiente etapa: Semana 5. Motor de recuperación (retriever)

- Implementar una función reutilizable de recuperación sobre el corpus indexado.
- Definir un conjunto fijo de preguntas de prueba y los fragmentos o fundamentos esperados para cada pregunta.
- Establecer un criterio explícito para considerar correcta una recuperación.
- Ejecutar las pruebas y documentar una métrica real, mediante precisión/recall o calificación manual.
- Registrar los errores de recuperación y las limitaciones identificadas.


## Actualización de seguimiento — 18 de octubre de 2026
### Recuperador híbrido, consulta estructurada de la Tabla 22 y preparación de operación reproducible

#### Trabajo realizado

- Se incorporó `retrieve_land_use()` en `retriever.py` para consultar `land_use_compatibility` por actividad y zonificación, sin sustituir la búsqueda semántica existente.
- Se añadieron las opciones de CLI `--activity` y `--zonification`; la modalidad semántica conserva la forma de uso anterior: `python retriever.py "pregunta" --top-k 5`.
- Se comprobó que la consulta estructurada devuelve los estados originales de la Tabla 22, la referencia del archivo y las páginas, y conserva `pendiente_revision: true`.
- Se probaron la coincidencia exacta de «Vivienda» en H (`permitido`) y E (`prohibido`), el alias «inhumación» (`por validar`), una actividad inexistente, una zonificación inválida y una actividad vacía.
- Se consultó «Centros nocturnos y discotecas» en H, HC, HO, HM, HCS, E y EA. Las siete consultas devolvieron `prohibido`, con referencia a `PPCU_Hipodromo-80-81.pdf`, página 81, y `pendiente_revision: true`.
- Se ejecutó una prueba de regresión en una sola ejecución: la consulta estructurada y la búsqueda semántica devolvieron resultados, y todos los fragmentos semánticos mantuvieron `pendiente_revision: true`.
- La búsqueda semántica sobre obligaciones por ruido devolvió fragmentos pertinentes —incluidos los artículos 10, fracción XV, y 30 de la Ley de Establecimientos Mercantiles—, pero también resultados secundarios o irrelevantes. La consulta sobre uso de suelo para un bar no recuperó la celda de compatibilidad específica en sus primeros cinco resultados.

#### Evaluación técnica

La integración básica funciona. La similitud vectorial es útil para encontrar texto normativo, pero no debe sustituir la consulta de datos tabulares cuando la respuesta depende de una actividad y una zonificación concretas. La consulta estructurada responde el estado registrado en la Tabla 22, pero no determina automáticamente la zonificación real de un predio ni demuestra por sí sola que exista autorización definitiva para abrir un establecimiento.

Todos los datos jurídicos siguen pendientes de revisión. No se modificó `needs_review`/`pendiente_revision`, no se regeneraron embeddings y no se sustituyeron las fuentes originales.

#### Notas de arquitectura que deben conservarse para una fase posterior

1. Primero mantener operativo y verificable el MVP; no ampliar ahora el procesamiento de todas las tablas ni rediseñar la arquitectura prematuramente.
2. Después evaluar si la arquitectura actual es la más adecuada, no solo si funciona. En particular, revisar el tratamiento de las múltiples tablas de `PPCU_Hipodromo` y del `PDU_Cuauhtemoc`.
3. Revisar los JSON estructurados y los scripts de extracción/preprocesamiento: conservar las matrices tabulares, los rótulos originales, las páginas y los estados literales. No inferir que una celda ausente significa permitido o prohibido y no convertir `por validar` en una decisión definitiva.
4. Evitar duplicar el sistema de chunking ya existente. Las tablas especiales deben integrarse como representación estructurada complementaria del procesamiento actual, no como una segunda extracción paralela sin necesidad.
5. Revisar la precisión de los metadatos documentales: los programas urbanos usan secciones, cuadros, planos y tablas que no siempre equivalen a artículos de una ley. No etiquetar automáticamente una sección decimal como artículo jurídico tradicional.
6. La tabla `land_use_compatibility` actual representa la Tabla 22 de Hipódromo; no debe asumirse que ya resuelve las tablas/cuadros del PDU de Cuauhtémoc ni otras tablas del PPCU.

#### Operación reproducible y riesgo de pérdida de datos

Aurora en `terraform/dev` es efímera. `./terraform/dev-down.sh` destruye los recursos DEV y los datos almacenados dentro de Aurora, incluidas las tablas y los embeddings cargados. Antes de apagar, conservar los artefactos fuente y de embeddings fuera de Aurora, preferentemente en S3 y/o en el repositorio/entorno local según corresponda. Al reconstruir DEV hay que recrear o verificar el esquema y volver a cargar los documentos, chunks y embeddings; `dev-up.sh` por sí solo no restaura los datos.

La secuencia completa queda documentada en `Instructivo_operacion.md`. El cargador de embeddings debe ejecutarse desde el entorno virtual activo `.venv`. Inicializar el esquema no es lo mismo que poblarlo: los embeddings deben insertarse en `legal_embeddings` y asociarse a sus documentos/chunks mediante el cargador existente. Antes de una escritura, ejecutar primero el modo de validación documentado y revisar sus conteos; no regenerar los embeddings si el artefacto correcto ya existe.

#### Pendiente

- El ejecutor interactivo `scripts/probar_retriever.py` ya está documentado y disponible en el paquete de documentación; verificar que también esté presente en el árbol de trabajo del repositorio antes de versionar.
- Completar la evaluación semántica con un conjunto fijo de preguntas, fragmentos esperados y un criterio consistente de corrección. El resultado de Precision@5 descrito abajo es preliminar y corresponde a una sola pregunta; no representa la métrica global del retriever.
- Validar manualmente las citas y la vigencia jurídica antes de tratar los resultados como fundamentos confirmados.
- Antes de apagar/destruir DEV, verificar y conservar fuera de Aurora los archivos fuente, chunks, embeddings y datos estructurados necesarios para reconstruir el ambiente. Seguir la lista de comprobación del `Instructivo_operacion.md`.
- No se realizó commit ni push como parte de esta actualización. La actualización documental aún debe revisarse en el árbol de trabajo y después versionarse con autorización explícita.

#### Ampliación de evaluación semántica — 18 de octubre de 2026

- Se revisó la pregunta «¿Qué obligaciones tienen los establecimientos mercantiles para evitar que el ruido afecte a terceros?». Como referencias esperadas se identificaron los artículos 10, fracción XV, y 30 de la Ley de Establecimientos Mercantiles para la Ciudad de México. La evaluación es técnica y no constituye dictamen jurídico.
- Se comparó el ranking vectorial con un ranking híbrido que resta al valor de distancia una contribución textual limitada por `LEAST(relevancia_textual, 1.0) * 0.08`. Para esta consulta, el ajuste no cambió los primeros cinco resultados.
- Se diagnosticó el comportamiento de `plainto_tsquery('spanish', ...)`, que exige coincidencia de todos los términos normalizados. Se comparó de forma diagnóstica con una consulta OR sobre los mismos 20 candidatos vectoriales. La alternativa OR mejoró la posición de algunos candidatos —por ejemplo, una referencia al artículo 2, fracción XIV, pasó de la posición 19 a la 13—, pero no entró en los primeros cinco. Esta variante fue un diagnóstico específico, no una implementación general del retriever.
- Para esta única pregunta y bajo una etiqueta preliminar estricta de relevancia, se observaron dos resultados relevantes en los primeros cinco: Precision@5 = 2/5 = 40 %. No debe extrapolarse a otras preguntas ni presentarse como métrica final del sistema. Hace falta fijar etiquetas esperadas y repetir el procedimiento sobre el conjunto completo.
- Archivos locales de trabajo mencionados durante la evaluación: `tests/evaluacion_semana5.json`, `scripts/evaluar_semana5.py` y `scripts/diagnostico_ranking.py`. Confirmar que existan y revisar `git status` en el repositorio real antes de afirmar que están incluidos en el paquete de entrega.
- No se modificó el retriever para incorporar la variante OR; no se regeneraron embeddings ni se alteró `retrieve_land_use()`. Los resultados semánticos continúan marcados para revisión (`needs_review = true` / `pendiente_revision: true`).

#### Registro de Tabla 22 — datos estructurados

La Tabla 22 del `PPCU_Hipodromo-80-81.pdf` (páginas 80–81) se incorporó a `land_use_compatibility` como 357 celdas únicas: 51 actividades por siete zonificaciones (H, HC, HO, HM, HCS, E y EA). El conteo registrado fue de 31 estados `permitido`, 198 `por validar` y 128 `prohibido`. Las 357 celdas mantienen `needs_review = true`; se reportaron cero celdas incorrectas en la verificación efectuada, pero esto no equivale a validación jurídica definitiva. Los estados originales, las páginas y la procedencia deben conservarse. La cobertura no debe extrapolarse a otras tablas del PPCU ni a los cuadros del PDDU de Cuauhtémoc.

#### Estado de cierre AWS y control de versiones

Esta actualización documental no demuestra que Aurora se haya apagado ni que los cambios se hayan publicado en GitHub. Antes de ejecutar el apagado/destrucción de DEV, comprobar el estado real de AWS, conservar los artefactos de reconstrucción y confirmar que no se necesitan más pruebas en Aurora. Después, revisar `git diff --check`, `git status` y los cambios completos; solo realizar `git add`, `commit` y `push` cuando el usuario lo autorice expresamente.

Evaluación semántica del recuperador — 26 de octubre de 2026
Objetivo y alcance
Se ejecutó la batería de evaluación de la Semana 5 para observar el comportamiento del recuperador semántico sobre consultas relacionadas con los cinco instrumentos jurídicos del MVP. La ejecución incluyó 11 casos estructurados y 16 consultas semánticas, con un máximo previsto de cinco resultados por consulta.
La evaluación técnica no equivale a una validación jurídica. La pertinencia de un fragmento para una pregunta tampoco demuestra, por sí sola, que la norma esté vigente, que la cita sea exacta o que la respuesta jurídica derivada sea correcta.
Resultados estructurados
La ejecución registrada reportó 11 de 11 pruebas estructuradas aprobadas. Este resultado acredita que los casos incluidos satisficieron las comprobaciones implementadas por el ejecutor. No demuestra la corrección de todos los usos de suelo posibles ni la cobertura completa de las tablas y zonificaciones del corpus.
Resultados semánticos anotados manualmente
Se revisaron 16 consultas y 80 posiciones de resultados. Las etiquetas utilizadas fueron:
    • 2: relevancia directa.
    • 1: relevancia parcial.
    • 0: resultado irrelevante para la consulta.
Conteo de las anotaciones revisadas:
    • Relevancia directa (2): 21 de 80 resultados (26.25 %).
    • Relevancia parcial (1): 24 de 80 (30 %).
    • Irrelevantes (0): 35 de 80 (43.75 %).
    • Resultados con relevancia directa o parcial (1 o 2): 45 de 80 (56.25 %).
Si se consideran relevantes tanto los resultados directos como los parciales, la precisión provisional agregada entre los resultados anotados es 45/80 = 56.25 %. Este valor se puede interpretar como una Precision@5 agregada únicamente bajo estas condiciones: las 16 consultas tienen cinco resultados anotados cada una, y las etiquetas corresponden al orden de recuperación de la ejecución revisada. No debe confundirse con una métrica de calidad jurídica ni con una evaluación independiente de todas las consultas posibles.
Una consulta, HIP-SEM-002, no recuperó ningún resultado marcado como relevante entre sus cinco posiciones. Las anotaciones identificaron problemas de extracción de tablas, fragmentos incompletos, referencias normativas pertinentes que no aparecieron en el ranking y resultados que no respondían al aspecto específico de la pregunta.
Limitaciones de la evidencia
El ejecutor scripts/evaluar_semana5.py muestra solamente los primeros 500 caracteres de cada fragmento (fragmento[:500]). Por tanto, algunas observaciones de texto cortado pueden deberse a la presentación del registro y no necesariamente al contenido completo almacenado en la base de datos. Antes de atribuir el problema al chunking, hay que exportar y revisar el fragmento completo, su identificador y sus metadatos.
Las anotaciones también describen problemas que no se explican únicamente por el límite de presentación: extracción o representación deficiente de tablas, pérdida de contexto, fragmentos que combinan contenido discontinuo, referencias de artículo inadecuadas y ausencia de resultados pertinentes en algunas consultas.
El inventario registrado previamente contiene 1,235 chunks y 1,369 embeddings de 1,024 dimensiones. La diferencia de conteos requiere una auditoría de relaciones, identificadores, duplicados y reglas de asociación. La dimensión vectorial por sí sola no identifica el modelo de embeddings ni demuestra que exista un error. No debe modificarse el modelo ni regenerarse el conjunto de embeddings hasta verificar su procedencia y consistencia.
Decisiones y siguientes pasos
    1. Conservar la salida original de la ejecución y las anotaciones revisadas como evidencia histórica, sin sobrescribirlas.
    2. Mejorar el ejecutor para guardar, por ejecución, las consultas, los resultados completos, el orden, los identificadores estables de chunks, los metadatos, las distancias o puntuaciones, los errores y la configuración relevante.
    3. Persistir las anotaciones manuales en un archivo versionado que identifique de forma inequívoca la ejecución y cada resultado evaluado.
    4. Auditar extracción, chunking y metadatos. Diferenciar artículos legales de secciones, cuadros y tablas de programas urbanos; conservar el contexto necesario para interpretar cada fragmento.
    5. Auditar la asociación entre chunks y embeddings, el modelo y su versión, la dimensión, la normalización, la métrica de distancia y la coherencia entre el modelo usado para documentos y consultas.
    6. Comparar cambios de extracción, chunking, contexto o solapamiento mediante evaluaciones controladas contra una línea base. No cambiar simultáneamente varias etapas sin poder atribuir el efecto.
    7. Evaluar después, y por separado, alternativas de recuperación híbrida, expansión de sinónimos, filtros y reranking. No asumir que mejorarán los resultados sin medirlos.
    8. Repetir la batería estructurada y semántica después de cada cambio relevante, registrar regresiones y validar las citas y la vigencia normativa antes de usar los resultados como fundamento jurídico confirmado.
Estado de infraestructura y validación
Aurora PostgreSQL fue detenida por el usuario después de la ejecución evaluada. Los resultados del 26 de octubre son evidencia histórica; no representan una nueva ejecución posterior al apagado. Las pruebas de integración que dependan de Aurora deberán esperar a que exista una base de pruebas disponible y se haya verificado el procedimiento seguro de reconstrucción.
No se debe modificar la infraestructura terraform/base, cambiar needs_review = true ni pendiente_revision = true, ni reemplazar fuentes originales como parte de esta fase de diagnóstico.
Conclusión
La evaluación estructurada de la Semana 5 pasó los 11 casos incluidos, pero la evaluación semántica revela una calidad de recuperación insuficiente para considerar el recuperador validado: 56.25 % de los resultados anotados fueron directos o parcialmente pertinentes, y una consulta no recuperó resultados pertinentes en el top 5. La prioridad es mejorar la trazabilidad y diagnosticar extracción, chunking, metadatos y embeddings antes de modificar la estrategia de recuperación.
La aceptación del recuperador deberá basarse en un protocolo versionado, un conjunto fijo de consultas, anotaciones reproducibles, métricas explícitas, ausencia de regresiones críticas y revisión de las citas. El criterio formal de éxito se documentará en docs/protocolo_evaluacion_retriever.md y deberá aplicarse sobre una nueva ejecución reproducible; los resultados actuales constituyen la línea base inicial, no una aprobación final.


## Semana 6 — Generación de respuestas con citas
### Cierre técnico — 29 de octubre de 2026

### Objetivo

Implementar una función que reciba una pregunta en español y devuelva una respuesta generada con un único modelo de lenguaje y referencias a los fragmentos recuperados. La función debe poder ejecutarse y probarse desde la consola mediante una interfaz CLI.

El alcance de esta semana se limitó a resolver la arquitectura y comprobar la ejecución técnica del flujo. No se realizó una evaluación de calidad del recuperador ni una validación de la corrección jurídica de las respuestas.

### Implementación

Se incorporaron los siguientes archivos locales:

- `generar_respuesta.py`: función `answer_question()`, responsable de coordinar la recuperación de información, construir el contexto, invocar el modelo generativo y estructurar el resultado.
- `prompts/respuesta_legal.txt`: instrucciones utilizadas para generar respuestas en el contexto jurídico del proyecto.
- `scripts/responder_cli.py`: interfaz de terminal que recibe una pregunta y presenta el resultado en formato JSON.
- `tests/test_generar_respuesta.py`: pruebas unitarias de la función utilizando dependencias simuladas.

La función recibe una pregunta y admite parámetros para limitar el número de fragmentos recuperados y especificar el identificador del modelo. También permite inyectar dependencias para facilitar las pruebas.

La respuesta se estructura en campos como `status`, `question`, `answer`, `citations`, `limitations` y `model_id`.

Los fragmentos recuperados reciben identificadores temporales (`F1`, `F2`, etc.). La validación implementada comprueba que las referencias emitidas por el modelo correspondan a fragmentos que efectivamente se proporcionaron en el contexto. Esta comprobación no demuestra que la interpretación jurídica de cada cita sea correcta.

### Flujo de ejecución

La arquitectura implementada para esta prueba es:

Pregunta del usuario
  ↓
scripts/responder_cli.py
  ↓
answer_question()
  ↓
Retriever existente
  ↓
Amazon Bedrock — generación de embedding
  ↓
Aurora PostgreSQL + pgvector
  ↓
Fragmentos recuperados
  ↓
Construcción del contexto y del prompt
  ↓
Amazon Bedrock Converse — Claude Sonnet 4.6
  ↓
Validación de identificadores de cita
  ↓
Respuesta estructurada en JSON

Se reutilizó el recuperador existente. No se modificaron el esquema de Aurora, los embeddings, el proceso de ingesta ni la infraestructura Terraform.

### Configuración y conectividad verificadas

Para ejecutar la prueba integrada se comprobó lo siguiente:

- Aurora PostgreSQL Serverless v2 se encontraba en estado `available`.
- La instancia administrativa utilizada para el acceso mediante AWS Systems Manager aparecía como `Online`.
- Se abrió un túnel SSM desde el puerto local `15432` hacia el puerto PostgreSQL `5432` de Aurora.
- La prueba de conectividad TCP al puerto `127.0.0.1:15432` terminó correctamente.
- Se verificó la conexión mediante `psql` a la base `tododerechovecino`, con el usuario `tdv_admin`.
- El motor respondió como PostgreSQL 16.15.
- Se configuró la variable de entorno `BEDROCK_MODEL_ID` con el perfil `us.anthropic.claude-sonnet-4-6`.
- Se verificó que el perfil de inferencia de Claude Sonnet 4.6 estuviera en estado `ACTIVE` en `us-east-1`.

### Incidencias y resolución

**1. Variable de entorno del modelo**

La primera ejecución de la CLI devolvió el mensaje:

`Falta configurar la variable de entorno BEDROCK_MODEL_ID.`

Se resolvió configurando la variable en la terminal:

`export BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"`

**2. Acceso a Anthropic en Amazon Bedrock**

La siguiente ejecución devolvió `ResourceNotFoundException`. La prueba directa mediante Bedrock Runtime permitió identificar que faltaba presentar los datos de uso de Anthropic para la cuenta.

Se completó el formulario correspondiente en AWS. Posteriormente, la invocación directa de Claude mediante la operación Converse respondió:

`OK`

Con ello se confirmó que el modelo podía ser invocado desde la cuenta y región utilizadas.

**3. Prueba de integración**

Una vez habilitado el modelo, se volvió a ejecutar la CLI con una pregunta sobre las disposiciones que regulan los establecimientos mercantiles en la colonia Hipódromo.

La ejecución devolvió una estructura JSON con información de la pregunta, referencias a fragmentos recuperados, metadatos de las fuentes y el identificador del modelo.

La salida compartida incluyó el fragmento `F3`, procedente del Programa Parcial de Desarrollo Urbano Hipódromo, sección 6.3.

La respuesta también incluyó la advertencia:

`Al menos una fuente citada está marcada como pendiente de revisión; su contenido requiere validación jurídica.`

### Comando de ejecución

La interfaz puede ejecutarse desde la raíz del repositorio con:

`PYTHONPATH=. python scripts/responder_cli.py "¿Qué disposiciones regulan el funcionamiento de establecimientos mercantiles en la colonia Hipódromo?"`

La ejecución requiere:

- Entorno virtual Python activo.
- Variable `BEDROCK_MODEL_ID` configurada.
- Credenciales AWS y permisos para invocar los modelos necesarios.
- Acceso a Aurora mediante el túnel SSM.
- Variable `PGPASSFILE` configurada para la conexión PostgreSQL.

### Resultado y criterio de cierre

Se completó la prueba técnica de la función generadora mediante consola/CLI, utilizando el recuperador existente, Aurora PostgreSQL con pgvector y un único modelo generativo en Amazon Bedrock.

El flujo llegó a la generación y devolvió una respuesta estructurada con referencias a fragmentos recuperados.

Por tanto, se considera cumplido el objetivo técnico de la Semana 6: disponer de una función que recibe una pregunta y devuelve una respuesta con citas, probada mediante CLI.

Este resultado acredita la integración técnica ejecutada. No acredita la pertinencia jurídica de los fragmentos recuperados, la vigencia de las disposiciones ni la corrección de las conclusiones generadas.

### Limitaciones que se conservan

- Los identificadores de cita `F1`, `F2`, etc. son temporales.
- La validación de citas comprueba la existencia de los identificadores entre las fuentes proporcionadas al modelo, no la correspondencia jurídica entre cada afirmación y su fundamento.
- Los fragmentos mantienen el indicador `pendiente_revision`; no se modificó su estado.
- No se evaluó la calidad de recuperación ni se calcularon métricas nuevas.
- No se integró todavía la consulta estructurada `retrieve_land_use()` en el flujo de generación.
- La prueba se realizó desde el entorno local mediante CLI. No representa todavía una integración con API Gateway, Lambda o frontend.

### Archivos de la entrega

- `generar_respuesta.py`
- `prompts/respuesta_legal.txt`
- `scripts/responder_cli.py`
- `tests/test_generar_respuesta.py`

### Siguiente etapa

La siguiente etapa se definirá conforme al cronograma de la estancia. La implementación actual queda como base para continuar la integración del MVP, sin ampliar en este cierre el alcance de la evaluación jurídica ni modificar la arquitectura acordada.
