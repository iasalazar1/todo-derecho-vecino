# Instructivo de operación

## Todo Derecho Vecino

**Proyecto:** Todo Derecho Vecino
**Repositorio:** `todo-derecho-vecino`
**Rama de desarrollo:** `mvp-estancia`
**Infraestructura:** AWS + Terraform
**Región:** `us-east-1`

---

## 1. Propósito

Este documento describe la operación cotidiana de la infraestructura de desarrollo de **Todo Derecho Vecino**.

El proyecto utiliza dos conjuntos de infraestructura administrados mediante Terraform:

* `terraform/base`: recursos persistentes.
* `terraform/dev`: recursos efímeros utilizados durante el desarrollo y las pruebas.

La separación permite apagar completamente el ambiente de desarrollo cuando no se está trabajando, reduciendo costos y evitando que la infraestructura temporal permanezca activa innecesariamente.

La infraestructura debe poder reconstruirse a partir del código Terraform.

---

## 2. Organización de Terraform

La infraestructura está separada de la siguiente manera:

```text
terraform/
├── base/
│   ├── iam.tf
│   ├── providers.tf
│   ├── s3.tf
│   ├── variables.tf
│   └── terraform.tfstate
│
├── dev/
│   ├── access.tf
│   ├── aurora.tf
│   ├── network.tf
│   ├── providers.tf
│   ├── variables.tf
│   └── terraform.tfstate
│
├── dev-up.sh
├── dev-down.sh
├── dev-status.sh
└── plan-semana3.txt
```

### 2.1 Recursos persistentes — `terraform/base`

La infraestructura BASE contiene actualmente:

* bucket S3 para los documentos jurídicos;
* configuración de acceso público del bucket;
* cifrado del bucket;
* versionado del bucket;
* rol IAM utilizado para despliegues Terraform;
* política asociada al rol IAM;
* información de la cuenta AWS utilizada por Terraform.

Estos recursos **no deben destruirse durante la operación normal de DEV**.

El bucket S3 tiene `prevent_destroy = true`.

El rol IAM de despliegue también tiene `prevent_destroy = true`.

### 2.2 Recursos efímeros — `terraform/dev`

El ambiente DEV contiene:

* VPC;
* subredes privadas;
* tabla de rutas;
* asociaciones de subredes;
* Security Groups;
* Aurora PostgreSQL Serverless v2;
* instancia Aurora;
* DB subnet group;
* EC2 temporal `admin_test`;
* IAM role de `admin_test`;
* instance profile;
* VPC endpoints para SSM;
* reglas de seguridad necesarias para la administración y conectividad.

Todos estos recursos forman parte del ciclo de desarrollo y pueden ser destruidos y reconstruidos.

---

# 3. Regla fundamental de operación

**Nunca ejecutar `terraform destroy` desde la raíz histórica `terraform/` ni intentar destruir BASE para apagar DEV.**

El ambiente que se desea apagar es exclusivamente:

```text
terraform/dev
```

La operación normal es:

```text
DEV-UP
   ↓
Desarrollo y pruebas
   ↓
DEV-DOWN
```

Cuando se vuelva a trabajar:

```text
DEV-UP
   ↓
Reconstrucción desde Terraform
   ↓
Desarrollo y pruebas
```

---

# 4. Encender el ambiente DEV

Desde la raíz del repositorio:

```bash
cd ~/todo-derecho-vecino
```

Ejecutar:

```bash
./terraform/dev-up.sh
```

El script:

1. inicializa Terraform en `terraform/dev`;
2. genera un `terraform plan`;
3. muestra los cambios que serán realizados;
4. solicita confirmación;
5. ejecuta `terraform apply`;
6. muestra los outputs resultantes.

La confirmación solicitada es:

```text
APPLY
```

No confirmar el `apply` si el plan muestra recursos BASE o acciones que no correspondan al ambiente DEV.

---

# 5. Verificar el ambiente DEV

Desde la raíz del repositorio:

```bash
./terraform/dev-status.sh
```

Cuando DEV está activo, deben poder observarse:

* recursos registrados en el estado de Terraform;
* endpoint de Aurora;
* nombre de la base de datos;
* puerto PostgreSQL;
* instancia EC2 `admin_test`;
* estado de Aurora;
* estado de la instancia Aurora;
* estado de la EC2.

Una situación normal con DEV apagado es:

```text
=== Terraform state ===

=== Terraform outputs ===
Warning: No outputs found
```

seguida de mensajes indicando que Aurora y la EC2 no están registradas.

Esto **no representa un error** cuando el ambiente DEV ha sido destruido correctamente.

---

# 6. Estado esperado de Aurora

La infraestructura actual utiliza:

```text
Motor:              aurora-postgresql
Versión:            16.15
Modo:               Serverless v2
Single-AZ
Min capacity:       0.5 ACU
Max capacity:       2 ACU
Puerto:             5432
Acceso público:     No
Cifrado en reposo:  Sí
```

El recurso se define en:

```text
terraform/dev/aurora.tf
```

La instancia utiliza:

```text
db.serverless
```

Aurora es un recurso **efímero** dentro del ambiente DEV.

Por esta razón, la información jurídica fuente no debe depender exclusivamente de Aurora.

La estrategia del proyecto es:

```text
S3
 ↓
documentos jurídicos
 ↓
chunking
 ↓
embeddings
 ↓
Aurora PostgreSQL + pgvector
```

Si Aurora se destruye, el índice deberá poder reconstruirse a partir de los documentos almacenados en S3.

---

# 7. Credenciales de Aurora

Aurora utiliza:

```hcl
manage_master_user_password = true
```

Por lo tanto, Terraform **no administra ni almacena directamente la contraseña maestra**.

AWS genera y administra la credencial mediante **AWS Secrets Manager**.

Esto significa que no es necesario modificar Terraform para introducir manualmente una contraseña antes de ejecutar:

```bash
./terraform/dev-up.sh
```

El proceso de encendido puede reconstruir Aurora sin que el usuario tenga que introducir la contraseña.

La contraseña solamente debe recuperarse cuando sea necesario realizar una conexión administrativa a PostgreSQL.

### Importante

Cada reconstrucción de Aurora puede generar una nueva credencial administrada por AWS.

No debe suponerse que una contraseña utilizada durante una ejecución anterior continuará siendo válida después de destruir y reconstruir Aurora.

---

# 8. Acceso administrativo a Aurora

Aurora no tiene acceso público.

El acceso administrativo se realiza mediante:

```text
Mac
 ↓
AWS Systems Manager
 ↓
EC2 admin_test
 ↓
Aurora PostgreSQL
```

La EC2 `admin_test` es temporal y existe únicamente para administración y pruebas durante el desarrollo.

---

# 9. Conectividad mediante SSM

Cuando DEV está activo, la instancia `admin_test` debe estar registrada en Systems Manager.

Puede verificarse mediante AWS CLI.

Después puede establecerse un túnel desde la computadora local hacia Aurora utilizando SSM.

Ejemplo:

```bash
aws ssm start-session \
  --target <INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["<AURORA_ENDPOINT>"],"portNumber":["5432"],"localPortNumber":["5432"]}'
```

El endpoint y el ID de la instancia deben obtenerse del estado actual de Terraform:

```bash
terraform -chdir=terraform/dev output
```

No deben reutilizarse endpoints o IDs obtenidos de una ejecución anterior si DEV fue destruido y reconstruido.

---

# 10. Conexión mediante `psql`

Con el túnel SSM activo, abrir otra terminal local y ejecutar:

```bash
psql -h localhost -p 5432 -U tdv_admin -d tododerechovecino
```

La contraseña debe obtenerse del secreto actual administrado por AWS Secrets Manager.

Una conexión correcta permite verificar:

```sql
SELECT current_database(), current_user, version();
```

---

# 11. Verificación de pgvector

La extensión `vector` es una extensión de PostgreSQL que se habilita a nivel de base de datos.

Después de una reconstrucción de Aurora, comprobar su existencia:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

Si todavía no está instalada:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Posteriormente verificar:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

En las pruebas realizadas durante la semana 3 se verificó:

```text
vector | 0.8.2
```

### Estado actual de automatización

La creación de la infraestructura Aurora está automatizada mediante Terraform.

La creación de la extensión PostgreSQL y la inicialización posterior de la base de datos todavía forman parte de la preparación de la base de datos y no están actualmente gestionadas por Terraform.

Esto deberá revisarse al avanzar hacia la ingesta de la semana 4.

---

# 12. Apagar el ambiente DEV

Desde la raíz del repositorio:

```bash
cd ~/todo-derecho-vecino
```

Ejecutar:

```bash
./terraform/dev-down.sh
```

El script:

1. genera un plan de destrucción;
2. muestra los recursos que serán eliminados;
3. solicita confirmación;
4. destruye únicamente el estado administrado por `terraform/dev`.

La confirmación requerida es:

```text
DESTROY
```

No confirmar si aparecen recursos de `terraform/base`.

---

# 13. Verificación después de apagar DEV

Después de ejecutar `dev-down`:

```bash
./terraform/dev-status.sh
```

El estado esperado es que no existan recursos DEV administrados por Terraform.

Después comprobar BASE:

```bash
terraform -chdir=terraform/base plan
```

El resultado esperado es:

```text
No changes.
Your infrastructure matches the configuration.
```

Esto confirma que el apagado de DEV no modificó la infraestructura persistente.

---

# 14. Ciclo completo de operación

El ciclo normal de desarrollo es:

### Encender

```bash
./terraform/dev-up.sh
```

### Verificar

```bash
./terraform/dev-status.sh
```

### Trabajar

Realizar desarrollo, pruebas de conectividad, pruebas de PostgreSQL, ingesta y demás actividades de la etapa correspondiente.

### Apagar

```bash
./terraform/dev-down.sh
```

### Verificar apagado

```bash
./terraform/dev-status.sh
```

### Verificar BASE

```bash
terraform -chdir=terraform/base plan
```

El resultado esperado de BASE es:

```text
No changes.
```

---

# 15. Recursos que deben sobrevivir a DEV-DOWN

Después de destruir DEV deben permanecer:

```text
S3
IAM deploy role
```

El bucket S3 es especialmente importante porque contiene o contendrá los documentos jurídicos fuente.

Aurora no debe considerarse el almacenamiento permanente del corpus original.

---

# 16. Recursos que deben desaparecer después de DEV-DOWN

Al apagar DEV deben desaparecer los recursos temporales, incluyendo:

```text
Aurora cluster
Aurora instance
EC2 admin_test
VPC
subnets
route table
security groups
SSM VPC endpoints
admin_test IAM role
admin_test instance profile
```

Esto permite evitar costos de recursos que no son necesarios mientras no se está desarrollando.

---

# 17. Terraform: procedimiento seguro

Antes de modificar infraestructura:

```text
1. Inspeccionar
2. Modificar
3. terraform fmt
4. terraform validate
5. terraform plan
6. Revisar el plan
7. Ejecutar apply solamente después de revisar
```

Para operaciones sobre el estado de Terraform:

```text
1. Hacer backup
2. Mostrar el estado actual
3. Ejecutar la operación de estado
4. Comprobar nuevamente el estado
5. Ejecutar terraform plan
```

No modificar manualmente los archivos `.tfstate`.

---

# 18. Evidencia de la separación BASE / DEV

La separación fue validada mediante el siguiente ciclo:

```text
Estado inicial
      ↓
Migración del estado Terraform
      ↓
terraform/base plan → No changes
terraform/dev plan  → No changes
      ↓
DEV-DOWN
      ↓
20 recursos DEV destruidos
      ↓
DEV-UP
      ↓
20 recursos DEV reconstruidos
      ↓
Pruebas de Aurora
      ↓
Prueba de conectividad
      ↓
Prueba de pgvector
      ↓
DEV-DOWN
      ↓
20 recursos DEV destruidos
      ↓
BASE plan → No changes
```

La segunda destrucción confirmó que el ambiente DEV puede apagarse completamente sin afectar los recursos persistentes.

---

# 19. Estado de la infraestructura después de la validación

Al finalizar la última prueba operativa:

```text
BASE: activo
DEV: apagado
Aurora: destruido
EC2 admin_test: destruida
VPC DEV: destruida
SSM endpoints: destruidos
S3: activo
IAM deploy role: activo
```

Este es el estado recomendado cuando no se está trabajando activamente en el desarrollo.

---

# 20. Próxima evolución

La siguiente etapa del proyecto corresponde a la ingesta y vectorización del corpus jurídico.

El flujo previsto es:

```text
Documentos jurídicos
        ↓
S3
        ↓
Extracción de texto
        ↓
Chunking
        ↓
Embeddings
        ↓
Aurora PostgreSQL
        ↓
pgvector
        ↓
Consultas de similitud
```

La automatización de la inicialización de la base de datos y de la reconstrucción del índice deberá evaluarse antes de depender de DEV-DOWN / DEV-UP como ciclo operativo completo.

El objetivo final es que Aurora pueda considerarse un índice reconstruible y que los documentos jurídicos originales permanezcan protegidos en S3.

---

## 21. Regla operativa final

Cuando se termine una sesión de desarrollo y no sea necesario mantener AWS activo:

```bash
./terraform/dev-down.sh
```

Cuando se vaya a continuar trabajando:

```bash
./terraform/dev-up.sh
```

La infraestructura persistente de `terraform/base` debe permanecer separada y protegida de las operaciones normales de DEV.

# Adenda. Inicialización del esquema jurídico (Semana 3) 
## Adenda: Propósito y límites `sql/001_initial_schema.sql` crea la estructura inicial para documentos jurídicos, chunks y segmentos vectorizados. 
No ingiere documentos ni embeddings. `scripts/init_db.sh` consulta Aurora, obtiene la instancia administrativa desde Terraform, verifica SSM, recupera la credencial desde Secrets Manager, abre un túnel privado y ejecuta el SQL. Tablas esperadas: - `legal_documents`: metadatos del instrumento y claves de artefactos en S3. - `legal_chunks`: texto original de cada chunk, referencia normativa y metadatos. - `legal_embeddings`: segmentos y vectores `vector(1024)` asociados al chunk y al documento. Se conserva `legal_chunks` como salida del procesador documental existente. No se crea un segundo sistema paralelo de chunking. El índice HNSW queda pospuesto hasta después de la carga y la evaluación de recursos. ## 13.2 Estado y precondiciones **Estado registrado al 10 de octubre de 2026:** Aurora no existe porque el ambiente `terraform/dev` está apagado intencionalmente. Esto no constituye por sí mismo un fallo. La prueba de esta sección comienza reconstruyendo DEV mediante el procedimiento autorizado. Antes de ejecutar `scripts/init_db.sh`: 1. Estar en la raíz del repositorio y en la rama de trabajo acordada (`mvp-estancia`). 2. Haber encendido DEV conscientemente con `./terraform/dev-up.sh` y revisado el plan antes de escribir `APPLY`. 3. Confirmar que Aurora esté `available` y que `terraform -chdir=terraform/dev output -raw admin_test_instance_id` corresponda al despliegue activo. 4. Confirmar que la instancia administrativa aparezca `Online` en SSM. 5. Tener instalados AWS CLI, Terraform, `psql`, `pg_isready`, Python 3 y `session-manager-plugin`. 6. Confirmar que el puerto local `15432` esté libre. 7. Confirmar que el secreto administrado de Aurora esté disponible. Nunca imprimir su contenido. ## 13.3 Procedimiento `terraform/dev-up.sh` ejecuta `terraform init`, muestra `terraform plan`, solicita escribir exactamente `APPLY`, ejecuta `terraform apply -auto-approve` y muestra los outputs. El mensaje final del script no sustituye las comprobaciones de disponibilidad y conectividad. Cuando el usuario autorice y DEV esté listo: ```bash bash -n scripts/init_db.sh git diff --check ./scripts/init_db.sh ``` El inicializador prueba la conexión PostgreSQL, aplica el SQL y verifica la extensión `vector`, las tres tablas y el tipo de `legal_embeddings.embedding` como `vector(1024)`. El éxito no significa que los documentos o embeddings estén cargados. ## 13.4 Apagado de DEV Aurora y la EC2 administrativa pertenecen al ambiente efímero `terraform/dev`. `./terraform/dev-down.sh` puede destruir Aurora y los datos guardados dentro de la base. Los documentos y artefactos fuente deben permanecer en S3 bajo la infraestructura persistente de `terraform/base`. No ejecutar `terraform destroy` desde la raíz ni desde `terraform/base`. Antes de apagar DEV, registrar evidencia y pedir autorización explícita. ## 13.5 Fallos posibles y diagnóstico - **Estado Terraform ausente/desactualizado:** el inicializador espera `terraform/dev/terraform.tfstate` y consulta el output `admin_test_instance_id`. Si se cambia a backend remoto o workspace distinto, deberá adaptarse. - **Aurora inexistente/no disponible:** puede ser normal si DEV está apagado. Confirmar el estado antes de tratarlo como incidente. - **Secreto no disponible:** revisar `manage_master_user_password`, `MasterUserSecret` y permisos IAM; nunca mostrar `SecretString`. - **SSM no `Online`:** revisar perfil IAM, SSM Agent, endpoints privados, DNS, rutas y security groups. - **Túnel sin conexión:** revisar `/tmp/tdv-init-db-ssm.log` y la conectividad desde la EC2 hacia Aurora por TCP 5432. - **Puerto 15432 ocupado:** identificar al proceso propietario antes de actuar; no matar procesos desconocidos. - **Falta `pg_isready`:** instalar el cliente PostgreSQL local o ajustar la precondición. - **`CREATE EXTENSION vector` falla:** comprobar disponibilidad y permisos en la versión exacta de Aurora recién desplegada. No asumir que una verificación anterior se conserva después de reconstruir DEV. - **Esquema incompatible:** `CREATE TABLE IF NOT EXISTS` no migra tablas existentes. La verificación actual comprueba elementos esenciales, no todas las columnas, restricciones e índices. - **Error SQL:** `psql` usa `ON_ERROR_STOP`; detenerse y diagnosticar el primer error. No borrar tablas para “reparar” sin inspección. - **Modelo/dimensión de embeddings:** conservar `amazon.titan-embed-text-v2:0` y 1024 dimensiones. El inicializador no carga ni regenera embeddings. - **Costos:** registrar cuándo se enciende y apaga DEV y comprobar su estado final. ## 13.6 Evidencia mínima Registrar sin secretos: outputs de Terraform, estado `available` de Aurora, versión del motor, estado `Online` de SSM, salida del inicializador, versión de `vector`, nombres de las tres tablas, tipo `vector(1024)`, resultado de `git status --short` y si DEV queda encendido o apagado. No marcar la Semana 3 como completada hasta que la base esté desplegada y accesible desde el entorno de prueba y se hayan registrado las comprobaciones reales. 
