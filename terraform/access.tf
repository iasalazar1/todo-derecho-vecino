# ============================================================
# Acceso temporal de administración para Semana 3
# EC2 privado + AWS Systems Manager Session Manager
# ============================================================

resource "aws_security_group" "admin_test" {
  name        = "todo-derecho-vecino-admin-test-sg"
  description = "Temporary SG for Week 3 administration EC2"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Allow outbound traffic from admin test instance"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "todo-derecho-vecino-admin-test-sg"
    Project = "todo-derecho-vecino"
  }
}

# Aurora acepta PostgreSQL solamente desde el EC2 de administración.
resource "aws_vpc_security_group_ingress_rule" "aurora_from_admin_test" {
  security_group_id            = aws_security_group.aurora.id
  referenced_security_group_id = aws_security_group.admin_test.id

  ip_protocol = "tcp"
  from_port   = 5432
  to_port     = 5432

  description = "PostgreSQL access from temporary Week 3 admin EC2"
}

# ------------------------------------------------------------
# IAM para Systems Manager
# ------------------------------------------------------------

resource "aws_iam_role" "admin_test_ssm" {
  name = "TodoDerechoVecino-AdminTest-SSM"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "ec2.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "TodoDerechoVecino-AdminTest-SSM"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_iam_role_policy_attachment" "admin_test_ssm" {
  role       = aws_iam_role.admin_test_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "admin_test" {
  name = "TodoDerechoVecino-AdminTest-SSM"

  role = aws_iam_role.admin_test_ssm.name
}

# ------------------------------------------------------------
# VPC Endpoints para Systems Manager
# ------------------------------------------------------------

resource "aws_vpc_endpoint" "ssm" {
  vpc_id = aws_vpc.main.id

  service_name = "com.amazonaws.${var.aws_region}.ssm"

  vpc_endpoint_type = "Interface"

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  security_group_ids = [
    aws_security_group.admin_test.id
  ]

  private_dns_enabled = true

  tags = {
    Name    = "todo-derecho-vecino-ssm-endpoint"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id = aws_vpc.main.id

  service_name = "com.amazonaws.${var.aws_region}.ssmmessages"

  vpc_endpoint_type = "Interface"

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  security_group_ids = [
    aws_security_group.admin_test.id
  ]

  private_dns_enabled = true

  tags = {
    Name    = "todo-derecho-vecino-ssmmessages-endpoint"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id = aws_vpc.main.id

  service_name = "com.amazonaws.${var.aws_region}.ec2messages"

  vpc_endpoint_type = "Interface"

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  security_group_ids = [
    aws_security_group.admin_test.id
  ]

  private_dns_enabled = true

  tags = {
    Name    = "todo-derecho-vecino-ec2messages-endpoint"
    Project = "todo-derecho-vecino"
  }
}

# ------------------------------------------------------------
# EC2 temporal para pruebas de PostgreSQL
# ------------------------------------------------------------

resource "aws_instance" "admin_test" {
  ami           = "ami-0d27e0fb3bac4d724"
  instance_type = "t3.micro"

  subnet_id = aws_subnet.private_a.id

  vpc_security_group_ids = [
    aws_security_group.admin_test.id
  ]

  iam_instance_profile = aws_iam_instance_profile.admin_test.name

  associate_public_ip_address = false

  tags = {
    Name    = "todo-derecho-vecino-admin-test"
    Project = "todo-derecho-vecino"
    Purpose = "Semana 3 PostgreSQL access test"
  }
}

resource "aws_vpc_security_group_ingress_rule" "admin_test_https" {
  security_group_id = aws_security_group.admin_test.id

  referenced_security_group_id = aws_security_group.admin_test.id

  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443

  description = "HTTPS from admin EC2 to SSM VPC endpoints"
}
