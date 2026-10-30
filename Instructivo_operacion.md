# Instructivo de operación — Todo Derecho Vecino

**Repositorio:** `iasalazar1/todo-derecho-vecino`  
**Rama:** `mvp-estancia`  
**Región AWS:** `us-east-1`  
**Base de datos:** Aurora PostgreSQL `tododerechovecino`  
**Modelo generativo:** Claude Sonnet 4.6 mediante Amazon Bedrock

Este instructivo contiene el procedimiento habitual para reconstruir el ambiente de desarrollo, restaurar los datos de Aurora, ejecutar las pruebas del RAG y apagar DEV. Está pensado para ejecutarse desde la raíz del repositorio.

---

## 1. Antes de empezar

En una terminal:

```bash
cd ~/todo-derecho-vecino
git switch mvp-estancia
git pull origin mvp-estancia
```

Comprueba que estás en la rama correcta y revisa si tienes cambios locales antes de continuar:

```bash
git status --short
```

Se requiere:

- AWS CLI configurado y con credenciales vigentes.
- Terraform.
- Python 3 y el entorno virtual del proyecto.
- `psql`, `pg_isready` y `session-manager-plugin`.
- Permisos AWS para Terraform, SSM, RDS, Secrets Manager, S3 y Bedrock.
- Los cinco JSON de chunks configurados para el corpus MVP y el JSON fuente de la Tabla 22.

Activa el entorno virtual:

```bash
source .venv/bin/activate
```

Si el entorno virtual no existe, créalo y reinstala las dependencias que utiliza el proyecto según su configuración vigente. No continúes si faltan los archivos fuente del corpus. No sustituyas archivos revisados por respaldos o versiones antiguas.

---

## 2. Reconstruir la infraestructura AWS

El proyecto separa los recursos en dos estados Terraform:

- `terraform/base`: recursos persistentes, principalmente S3 e IAM.
- `terraform/dev`: red, Aurora PostgreSQL y la instancia temporal `admin_test` para acceso por SSM.

Desde la raíz del repositorio:

```bash
./terraform/dev-up.sh
```

El script inicializa Terraform, muestra el plan y solicita escribir exactamente:

```text
APPLY
```

Lee el plan antes de confirmar. Debe corresponder exclusivamente a `terraform/dev`. Si aparecen acciones sobre `terraform/base`, recursos inesperados o destrucciones no previstas, cancela.

Después verifica:

```bash
./terraform/dev-status.sh
```

Antes de seguir, confirma:

- Aurora está en estado `available`.
- La instancia Aurora está disponible.
- `admin_test` está en ejecución y aparece `Online` en Systems Manager.

La reconstrucción de Terraform **no restaura el contenido de PostgreSQL**. Aurora es efímera: al destruir DEV se pierden las tablas y los registros almacenados en ella.

---

## 3. Inicializar el esquema de PostgreSQL

Ejecuta desde la raíz:

```bash
./scripts/init_db.sh
```

Este script automatiza el acceso inicial: consulta Aurora, obtiene la instancia `admin_test`, verifica SSM, recupera la credencial vigente desde Secrets Manager, abre un túnel temporal y aplica `sql/001_initial_schema.sql`.

Al terminar verifica la extensión `vector`, las tablas `legal_documents`, `legal_chunks` y `legal_embeddings`, y el tipo `vector(1024)` de la columna de embeddings.

**Este paso no carga documentos, chunks ni embeddings.** El túnel que abre el script se cierra al terminar.

---

## 4. Recuperar el archivo de embeddings desde S3

El archivo completo utilizado en la carga del corpus se conserva en el bucket persistente de S3, en esta clave:

```text
mvp/embeddings/embeddings_mvp.jsonl
```

Crea el directorio local y descarga el artefacto:

```bash
mkdir -p salida
aws s3 cp \
  s3://todo-derecho-vecino-857385469837-us-east-1/mvp/embeddings/embeddings_mvp.jsonl \
  salida/embeddings_mvp.jsonl \
  --region us-east-1
```

Comprueba que el archivo exista y tenga contenido:

```bash
ls -lh salida/embeddings_mvp.jsonl
```

Si el objeto no existe o no se puede descargar, detente y revisa el bucket y sus objetos. No regeneres embeddings automáticamente ni sobrescribas el artefacto persistido. La generación con Titan puede implicar consumo de Bedrock y debe tratarse como una operación separada.

El artefacto corresponde a `amazon.titan-embed-text-v2:0`, con vectores de 1,024 dimensiones. Debe corresponder a los chunks configurados en `documentos_config_mvp.json`.

---

## 5. Preparar el acceso PostgreSQL para las cargas

`init_db.sh` usa una credencial temporal para inicializar el esquema. Para las cargas posteriores se necesita un archivo `.pgpass` persistente y protegido, y un túnel SSM abierto en otra terminal.

### 5.1 Crear o actualizar el archivo de credenciales

Obtén el ARN del secreto vigente de Aurora:

```bash
export TDV_SECRET_ARN="$(
  aws rds describe-db-clusters \
    --region us-east-1 \
    --db-cluster-identifier todo-derecho-vecino-aurora \
    --query 'DBClusters[0].MasterUserSecret.SecretArn' \
    --output text
)"
```

Crea el archivo protegido sin imprimir la contraseña:

```bash
python - <<'PY'
import boto3
import json
import os
from pathlib import Path

region = "us-east-1"
secret_arn = os.environ["TDV_SECRET_ARN"]
secret = boto3.client("secretsmanager", region_name=region).get_secret_value(
    SecretId=secret_arn
)
credentials = json.loads(secret["SecretString"])
password = credentials["password"]

def escape(value):
    return value.replace("\\", "\\\\").replace(":", "\\:")

path = Path.home() / ".pgpass-todo-derecho-vecino"
line = "127.0.0.1:15432:tododerechovecino:tdv_admin:" + escape(password) + "\n"
path.write_text(line, encoding="utf-8")
path.chmod(0o600)
print(f"Archivo de credenciales preparado: {path}")
PY

export PGPASSFILE="$HOME/.pgpass-todo-derecho-vecino"
```

No abras, imprimas, copies ni subas este archivo al repositorio. Si cambia la credencial al reconstruir Aurora, vuelve a generarlo.

### 5.2 Abrir el túnel SSM

Abre una segunda terminal, entra al repositorio y activa `.venv`. Ejecuta:

```bash
INSTANCE_ID="$(
  terraform -chdir=terraform/dev output -raw admin_test_instance_id
)"

AURORA_ENDPOINT="$(
  aws rds describe-db-clusters \
    --region us-east-1 \
    --db-cluster-identifier todo-derecho-vecino-aurora \
    --query 'DBClusters[0].Endpoint' \
    --output text
)"

aws ssm start-session \
  --region us-east-1 \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$AURORA_ENDPOINT\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"15432\"]}"
```

Mantén esta terminal abierta mientras realizas las cargas y pruebas. El puerto local `15432` debe estar libre. Para cerrar el túnel, termina la sesión con `Ctrl+C`.

En la primera terminal, confirma que PostgreSQL responde:

```bash
pg_isready -h 127.0.0.1 -p 15432
```

---

## 6. Cargar documentos, chunks y embeddings

Con `.venv` activo, `PGPASSFILE` configurado y el túnel SSM abierto, ejecuta primero la validación. Este comando no escribe en Aurora:

```bash
python scripts/load_embeddings.py \
  --embeddings salida/embeddings_mvp.jsonl
```

Revisa el resultado. Para la carga completa de referencia se esperan:

- 5 documentos.
- 1,235 chunks fuente.
- 1,369 segmentos de embeddings.
- Modelo `amazon.titan-embed-text-v2:0`.
- Dimensión 1,024.
- Ningún segmento faltante.

Si la validación es correcta, ejecuta la carga real añadiendo `--apply`:

```bash
python scripts/load_embeddings.py \
  --embeddings salida/embeddings_mvp.jsonl \
  --apply
```

La carga completa se realiza dentro de una transacción y sincroniza el corpus configurado. No ejecutes `--allow-incomplete` para reconstruir el corpus completo.

Si los conteos, el modelo, la dimensión o los archivos no coinciden, detente. No fuerces la carga ni regeneres vectores para ocultar una discrepancia.

---

## 7. Restaurar la Tabla 22 de compatibilidad de uso de suelo

La tabla `land_use_compatibility` es independiente de los embeddings. Su fuente es:

```text
leyes_cdmx/PPCU_Hipodromo_tabla_22.json
```

Primero valida el archivo, sin modificar Aurora:

```bash
python scripts/load_land_use_compatibility.py
```

La referencia registrada es de 51 actividades y 357 celdas (siete zonificaciones por actividad). Si la validación es correcta, importa los registros:

```bash
python scripts/load_land_use_compatibility.py --apply
```

Los registros conservan `needs_review = true`. La importación no constituye una validación jurídica de la Tabla 22.

---

## 8. Probar recuperación y generación de respuestas

### 8.1 Probar el recuperador

Con el túnel SSM abierto y `PGPASSFILE` configurado:

```bash
python scripts/probar_retriever.py
```

El ejecutor ofrece dos opciones:

1. Búsqueda semántica de fragmentos.
2. Consulta estructurada de la Tabla 22 por actividad y zonificación.

Comprueba que los resultados incluyan metadatos y referencias. La similitud vectorial no demuestra por sí sola pertinencia ni aplicabilidad jurídica.

### 8.2 Configurar Claude Sonnet 4.6

En la terminal que ejecutará la CLI:

```bash
export AWS_REGION="us-east-1"
export BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"
```

La cuenta debe tener habilitada la invocación del modelo y los permisos necesarios para Bedrock. Titan se utiliza para generar embeddings de consulta; Claude Sonnet 4.6 es el único modelo generativo del flujo.

### 8.3 Ejecutar una consulta de punta a punta desde CLI

```bash
PYTHONPATH=. python scripts/responder_cli.py \
  "¿Qué disposiciones regulan el funcionamiento de establecimientos mercantiles en la colonia Hipódromo?"
```

La salida JSON debe contener `status`, `question`, `answer`, `citations`, `limitations` y `model_id`.

El resultado confirma la integración técnica pregunta → recuperación → generación → citas. No acredita por sí solo la corrección jurídica, vigencia normativa ni pertinencia de cada fragmento. Si una fuente aparece pendiente de revisión, conserva esa advertencia.

---

## 9. Apagar DEV

Cuando terminen las pruebas, cierra el túnel SSM (`Ctrl+C`) y vuelve a la terminal principal.

Antes de destruir DEV, asegúrate de que no necesitas conservar datos nuevos almacenados únicamente en Aurora. El contenido de Aurora se pierde al destruir el ambiente. Los artefactos fuente y el JSONL de embeddings deben permanecer respaldados fuera de Aurora, preferentemente en S3.

Ejecuta:

```bash
./terraform/dev-down.sh
```

Lee el plan de destrucción. El script solicita escribir exactamente:

```text
DESTROY
```

Confirma solo si el plan afecta exclusivamente a `terraform/dev`. No ejecutes `terraform destroy` desde la raíz ni desde `terraform/base`.

Verifica el apagado:

```bash
./terraform/dev-status.sh
terraform -chdir=terraform/base plan
```

El estado de DEV debe aparecer vacío o sin recursos activos. El plan de BASE debe indicar que no hay cambios. S3 y el rol IAM persistente deben conservarse.

---

## 10. Secuencia rápida para la siguiente sesión

Cuando DEV esté apagado, la secuencia de reconstrucción es:

1. `git pull origin mvp-estancia`.
2. `source .venv/bin/activate`.
3. `./terraform/dev-up.sh` y confirmar `APPLY` después de revisar el plan.
4. `./terraform/dev-status.sh`; esperar Aurora `available` y `admin_test` `Online`.
5. `./scripts/init_db.sh`.
6. Descargar `mvp/embeddings/embeddings_mvp.jsonl` desde S3 a `salida/`.
7. Actualizar `PGPASSFILE` con la credencial vigente.
8. Abrir el túnel SSM en una segunda terminal.
9. Validar y cargar `scripts/load_embeddings.py`.
10. Validar y cargar `scripts/load_land_use_compatibility.py`.
11. Probar `scripts/probar_retriever.py`.
12. Configurar `BEDROCK_MODEL_ID` y probar `scripts/responder_cli.py`.
13. Cerrar el túnel y ejecutar `./terraform/dev-down.sh` cuando terminen las pruebas.

**Orden clave:** Terraform → inicialización del esquema → restauración de artefactos → carga de datos → pruebas del recuperador → prueba de Claude. No se debe saltar directamente de Terraform a las pruebas de Sonnet.

---

## 11. Semana 7 — siguiente etapa de desarrollo

El siguiente objetivo del proyecto es **Backend serverless**:

- Implementar AWS Lambda y API Gateway.
- Exponer el flujo completo pregunta → recuperación → generación mediante un endpoint HTTP.
- Probar el endpoint de punta a punta.

El entregable será un endpoint de prueba que reciba una consulta y devuelva una respuesta con citas. La CLI documentada aquí seguirá siendo una referencia de prueba local del flujo implementado en Semana 6.

No se considera implementado Lambda ni API Gateway hasta que se complete y pruebe la Semana 7.
