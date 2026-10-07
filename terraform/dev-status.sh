#!/bin/bash

set -e

echo "=========================================="
echo " Todo Derecho Vecino - Estado DEV"
echo "=========================================="
echo

echo "=== Terraform state ==="
terraform -chdir=terraform/dev state list

echo
echo "=== Terraform outputs ==="
terraform -chdir=terraform/dev output

echo
echo "=== Aurora PostgreSQL ==="

CLUSTER_ID=$(terraform -chdir=terraform/dev output -raw aurora_database_name 2>/dev/null || true)

if [ -n "$CLUSTER_ID" ]; then
  aws rds describe-db-clusters \
    --db-cluster-identifier todo-derecho-vecino-aurora \
    --query 'DBClusters[0].{Status:Status,Engine:Engine,EngineVersion:EngineVersion,Endpoint:Endpoint,Port:Port}' \
    --output table
else
  echo "Aurora no está registrada en el estado de Terraform."
fi

echo
echo "=== Aurora instance ==="

aws rds describe-db-instances \
  --db-instance-identifier todo-derecho-vecino-aurora-instance \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,AZ:AvailabilityZone,Public:PubliclyAccessible}' \
  --output table 2>/dev/null || echo "Instancia Aurora no encontrada."

echo
echo "=== EC2 admin_test ==="

INSTANCE_ID=$(terraform -chdir=terraform/dev output -raw admin_test_instance_id 2>/dev/null || true)

if [ -n "$INSTANCE_ID" ]; then
  aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].{State:State.Name,InstanceId:InstanceId,Type:InstanceType,PrivateIP:PrivateIpAddress,Subnet:SubnetId,VPC:VpcId}' \
    --output table
else
  echo "EC2 admin_test no está registrada en el estado de Terraform."
fi

echo
echo "=========================================="
echo " Fin del estado DEV"
echo "=========================================="
