#!/usr/bin/env bash

set -Eeuo pipefail

REGION="us-east-1"
CLUSTER_ID="todo-derecho-vecino-aurora"
LOCAL_PORT="15432"
SQL_FILE="sql/001_initial_schema.sql"
SSM_LOG="/tmp/tdv-init-db-ssm.log"

TUNNEL_PID=""
DB_PASSWORD=""
PGPASSFILE_TEMP=""

cleanup() {
    if [[ -n "$PGPASSFILE_TEMP" ]]; then
        rm -f "$PGPASSFILE_TEMP"
    fi

    unset PGPASSWORD DB_PASSWORD SECRET_JSON 2>/dev/null || true

    if [[ -n "$TUNNEL_PID" ]]; then
        kill "$TUNNEL_PID" 2>/dev/null || true
        wait "$TUNNEL_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

echo "=== Todo Derecho Vecino: inicializacion del esquema ==="

# 1. Comprobar herramientas y archivos.
for cmd in aws terraform psql pg_isready python3; do
    command -v "$cmd" >/dev/null 2>&1 ||
        fail "No se encontro la herramienta requerida: $cmd"
done

command -v session-manager-plugin >/dev/null 2>&1 ||
    fail "Falta session-manager-plugin de AWS Systems Manager."

[[ -f "$SQL_FILE" ]] ||
    fail "No existe $SQL_FILE. Ejecuta el script desde la raiz del repositorio."

[[ -f "terraform/dev/terraform.tfstate" ]] ||
    fail "No existe el estado local de Terraform DEV. Comprueba que DEV este desplegado y que su estado este disponible."

# 2. Consultar Aurora.
echo "Consultando Aurora en AWS..."

CLUSTER_JSON="$(
    aws rds describe-db-clusters \
        --region "$REGION" \
        --db-cluster-identifier "$CLUSTER_ID" \
        --output json
)" || fail "No se pudo consultar Aurora. Comprueba el estado de DEV."

mapfile -t CLUSTER_FIELDS < <(
    printf '%s' "$CLUSTER_JSON" | python3 -c '
import json, sys

data = json.load(sys.stdin)
clusters = data.get("DBClusters", [])

if len(clusters) != 1:
    raise SystemExit("No se encontro exactamente un cluster Aurora.")

cluster = clusters[0]
secret = cluster.get("MasterUserSecret") or {}

for value in (
    cluster.get("Endpoint", ""),
    cluster.get("Port", ""),
    cluster.get("DatabaseName", ""),
    cluster.get("MasterUsername", ""),
    secret.get("SecretArn", ""),
    cluster.get("Status", ""),
):
    print(value)
'
) || fail "No se pudieron interpretar los datos del cluster."

[[ "${#CLUSTER_FIELDS[@]}" -eq 6 ]] ||
    fail "La respuesta de Aurora esta incompleta."

ENDPOINT="${CLUSTER_FIELDS[0]}"
DB_PORT="${CLUSTER_FIELDS[1]}"
DB_NAME="${CLUSTER_FIELDS[2]}"
DB_USER="${CLUSTER_FIELDS[3]}"
SECRET_ARN="${CLUSTER_FIELDS[4]}"
STATUS="${CLUSTER_FIELDS[5]}"

unset CLUSTER_JSON CLUSTER_FIELDS

[[ "$STATUS" == "available" ]] ||
    fail "Aurora no esta disponible. Estado actual: $STATUS"

[[ -n "$ENDPOINT" && -n "$DB_NAME" && -n "$DB_USER" && -n "$SECRET_ARN" ]] ||
    fail "Faltan datos del cluster o el ARN del secreto."

# 3. Obtener la instancia administrativa de Terraform.
INSTANCE_ID="$(
    terraform -chdir=terraform/dev output -raw admin_test_instance_id
)" || fail "No se pudo obtener admin_test_instance_id. Comprueba el estado de Terraform DEV."

[[ "$INSTANCE_ID" == i-* ]] ||
    fail "El ID de la instancia administrativa no parece valido."

# 4. Verificar que SSM reconoce la instancia.
echo "Comprobando la instancia administrativa en SSM..."

SSM_STATUS="$(
    aws ssm describe-instance-information \
        --region "$REGION" \
        --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text
)" || fail "No se pudo consultar Systems Manager."

[[ "$SSM_STATUS" == "Online" ]] ||
    fail "La instancia $INSTANCE_ID no esta Online en SSM."

# 5. Recuperar la contraseña sin imprimirla.
echo "Recuperando credenciales de Secrets Manager..."

SECRET_JSON="$(
    aws secretsmanager get-secret-value \
        --region "$REGION" \
        --secret-id "$SECRET_ARN" \
        --query SecretString \
        --output text
)" || fail "No se pudieron recuperar las credenciales."

DB_PASSWORD="$(
    printf '%s' "$SECRET_JSON" | python3 -c '
import json, sys

secret = json.load(sys.stdin)
password = secret.get("password")

if not isinstance(password, str) or not password:
    raise SystemExit("El secreto no contiene una contraseña valida.")

print(password, end="")
'
)" || fail "No se pudo interpretar la contraseña."

unset SECRET_JSON

[[ -n "$DB_PASSWORD" ]] ||
    fail "La contraseña recuperada esta vacia."

# 6. Evitar utilizar un puerto local ocupado.
if (echo >"/dev/tcp/127.0.0.1/$LOCAL_PORT") >/dev/null 2>&1; then
    fail "El puerto local $LOCAL_PORT ya esta ocupado. No se modifico."
fi

# 7. Abrir el tunel privado por SSM.
echo "Abriendo tunel SSM hacia Aurora..."

aws ssm start-session \
    --region "$REGION" \
    --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"host\":[\"$ENDPOINT\"],\"portNumber\":[\"$DB_PORT\"],\"localPortNumber\":[\"$LOCAL_PORT\"]}" \
    > "$SSM_LOG" 2>&1 &

TUNNEL_PID=$!

CONNECTED="false"

for _ in $(seq 1 30); do
    if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
        cat "$SSM_LOG" >&2
        fail "La sesion SSM termino antes de establecer el tunel."
    fi

    if pg_isready -h 127.0.0.1 -p "$LOCAL_PORT" -t 1 >/dev/null 2>&1; then
        CONNECTED="true"
        break
    fi

    sleep 1
done

[[ "$CONNECTED" == "true" ]] ||
    fail "PostgreSQL no respondio en 30 segundos. Revisa $SSM_LOG."

# 8. Preparar credenciales temporales para psql.
# El archivo tiene permisos restringidos y se elimina al terminar.
umask 077
PGPASSFILE_TEMP="$(mktemp)" ||
    fail "No se pudo crear el archivo temporal de credenciales."

TDV_DB_PASSWORD="$DB_PASSWORD" python3 - "$PGPASSFILE_TEMP" "$DB_USER" "$DB_NAME" "$LOCAL_PORT" <<'PY'
import os
import sys

path, user, database, port = sys.argv[1:]
password = os.environ.pop("TDV_DB_PASSWORD", "")

if not password:
    raise SystemExit("La contraseña está vacía.")

def escape(value):
    return value.replace("\\", "\\\\").replace(":", "\\:")

with open(path, "w", encoding="utf-8") as f:
    f.write(
        f"127.0.0.1:{escape(port)}:{escape(database)}:"
        f"{escape(user)}:{escape(password)}\n"
    )

os.chmod(path, 0o600)
PY

export PGPASSFILE="$PGPASSFILE_TEMP"
unset DB_PASSWORD

PSQL=(
    psql
    -X
    -v ON_ERROR_STOP=1
    -h 127.0.0.1
    -p "$LOCAL_PORT"
    -U "$DB_USER"
    -d "$DB_NAME"
)

# 9. Comprobar autenticacion antes de ejecutar el esquema.
echo "Probando autenticacion y conexion PostgreSQL..."

"${PSQL[@]}" -Atqc 'SELECT current_database(), current_user;' ||
    fail "No se pudo autenticar en PostgreSQL."

# 10. Aplicar el esquema.
echo "Aplicando $SQL_FILE..."

"${PSQL[@]}" -f "$SQL_FILE" ||
    fail "La ejecucion del esquema SQL fallo."

# 11. Verificar extension, tablas y dimension del vector.
echo "Verificando extension, tablas y dimension del vector..."

"${PSQL[@]}" <<'SQL'
DO $verify$
DECLARE
    table_name TEXT;
    embedding_type TEXT;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'vector'
    ) THEN
        RAISE EXCEPTION 'No esta instalada la extension vector.';
    END IF;

    FOREACH table_name IN ARRAY ARRAY[
        'legal_documents',
        'legal_chunks',
        'legal_embeddings'
    ]
    LOOP
        IF to_regclass('public.' || table_name) IS NULL THEN
            RAISE EXCEPTION 'Falta la tabla public.%', table_name;
        END IF;
    END LOOP;

    SELECT format_type(a.atttypid, a.atttypmod)
      INTO embedding_type
    FROM pg_attribute AS a
    WHERE a.attrelid = 'public.legal_embeddings'::regclass
      AND a.attname = 'embedding'
      AND NOT a.attisdropped;

    IF embedding_type IS DISTINCT FROM 'vector(1024)' THEN
        RAISE EXCEPTION
            'Dimension inesperada para embedding: %. Se esperaba vector(1024).',
            COALESCE(embedding_type, 'columna inexistente');
    END IF;
END
$verify$;

SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'legal_documents',
      'legal_chunks',
      'legal_embeddings'
  )
ORDER BY table_name;

SELECT format_type(a.atttypid, a.atttypmod) AS embedding_type
FROM pg_attribute AS a
WHERE a.attrelid = 'public.legal_embeddings'::regclass
  AND a.attname = 'embedding'
  AND NOT a.attisdropped;
SQL

echo
echo "Inicializacion y verificaciones finalizadas correctamente."
