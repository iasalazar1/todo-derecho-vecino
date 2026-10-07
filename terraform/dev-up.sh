#!/bin/bash

set -e

echo "=========================================="
echo " Todo Derecho Vecino - DEV UP"
echo "=========================================="
echo
echo "Este comando reconstruirá SOLAMENTE la infraestructura"
echo "administrada por terraform/dev."
echo
echo "S3 e IAM persistentes de terraform/base NO serán tocados."
echo

echo "=== INICIALIZANDO TERRAFORM DEV ==="
terraform -chdir=terraform/dev init

echo
echo "=== PLAN DE CREACIÓN ==="
terraform -chdir=terraform/dev plan

echo
read -r -p "¿Quieres continuar con la creación de DEV? Escribe 'APPLY': " CONFIRM

if [ "$CONFIRM" != "APPLY" ]; then
  echo
  echo "Operación cancelada."
  exit 0
fi

echo
echo "=== CREANDO DEV ==="
terraform -chdir=terraform/dev apply -auto-approve

echo
echo "=== ESTADO FINAL ==="
terraform -chdir=terraform/dev output

echo
echo "=========================================="
echo " DEV reconstruido."
echo "=========================================="

