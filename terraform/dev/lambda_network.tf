# ============================================================
# Semana 7 - Conectividad privada de AWS Lambda
# ============================================================

# ------------------------------------------------------------
# Security Group de Lambda
# ------------------------------------------------------------

resource "aws_security_group" "lambda" {
  name        = "todo-derecho-vecino-lambda-sg"
  description = "Security group for Todo Derecho Vecino Lambda"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name    = "todo-derecho-vecino-lambda-sg"
    Project = "todo-derecho-vecino"
  }
}

# Lambda -> Aurora PostgreSQL
resource "aws_vpc_security_group_egress_rule" "lambda_to_aurora" {
  security_group_id            = aws_security_group.lambda.id
  referenced_security_group_id = aws_security_group.aurora.id

  ip_protocol = "tcp"
  from_port   = 5432
  to_port     = 5432

  description = "Lambda to Aurora PostgreSQL"
}

# Aurora -> Lambda
resource "aws_vpc_security_group_ingress_rule" "aurora_from_lambda" {
  security_group_id            = aws_security_group.aurora.id
  referenced_security_group_id = aws_security_group.lambda.id

  ip_protocol = "tcp"
  from_port   = 5432
  to_port     = 5432

  description = "PostgreSQL access from Lambda"
}

# Lambda -> VPC endpoints
resource "aws_vpc_security_group_egress_rule" "lambda_to_endpoints" {
  security_group_id            = aws_security_group.lambda.id
  referenced_security_group_id = aws_security_group.lambda_endpoints.id

  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443

  description = "HTTPS from Lambda to AWS interface endpoints"
}

# ------------------------------------------------------------
# Security Group de los VPC Interface Endpoints
# ------------------------------------------------------------

resource "aws_security_group" "lambda_endpoints" {
  name        = "todo-derecho-vecino-lambda-endpoints-sg"
  description = "Security group for Lambda interface endpoints"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name    = "todo-derecho-vecino-lambda-endpoints-sg"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_from_lambda" {
  security_group_id            = aws_security_group.lambda_endpoints.id
  referenced_security_group_id = aws_security_group.lambda.id

  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443

  description = "HTTPS from Lambda"
}

# ------------------------------------------------------------
# VPC Interface Endpoints
#
# Se utiliza inicialmente private_a (us-east-1a) para limitar
# costos del ambiente de desarrollo.
# ------------------------------------------------------------

locals {
  lambda_interface_endpoints = toset([
    "bedrock-runtime",
    "secretsmanager",
    "logs"
  ])
}

resource "aws_vpc_endpoint" "lambda_services" {
  for_each = local.lambda_interface_endpoints

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Interface"

  subnet_ids = [
    aws_subnet.private_a.id
  ]

  security_group_ids = [
    aws_security_group.lambda_endpoints.id
  ]

  private_dns_enabled = true

  tags = {
    Name    = "todo-derecho-vecino-${each.value}-endpoint"
    Project = "todo-derecho-vecino"
  }
}
