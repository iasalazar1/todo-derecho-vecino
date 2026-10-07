#!/bin/bash

set -e

echo "=========================================="
echo " Todo Derecho Vecino - DEV DOWN"
echo "=========================================="
echo
echo "ATENCIÓN:"
echo "Este comando destruirá SOLAMENTE la infraestructura"
echo "administrada por terraform/dev."
echo
echo "S3 e IAM persistentes de terraform/base NO serán tocados."
echo

echo "=== PLAN DE DESTRUCCIÓN ==="
terraform -chdir=terraform/dev plan -destroy

echo
read -r -p "¿Quieres continuar con la destrucción de DEV? Escribe 'DESTROY': " CONFIRM

if [ "$CONFIRM" != "DESTROY" ]; then
  echo
  echo "Operación cancelada."
  exit 0
fi

echo
echo "=== DESTRUYENDO DEV ==="
terraform -chdir=terraform/dev destroy -auto-approve

echo
echo "=========================================="
echo " DEV destruido."
echo "=========================================="

