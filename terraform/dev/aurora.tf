resource "aws_db_subnet_group" "aurora" {
  name = "todo-derecho-vecino-aurora"

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  tags = {
    Name    = "todo-derecho-vecino-aurora-subnet-group"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_security_group" "aurora" {
  name        = "todo-derecho-vecino-aurora-sg"
  description = "Security group for Todo Derecho Vecino Aurora PostgreSQL"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name    = "todo-derecho-vecino-aurora-sg"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "todo-derecho-vecino-aurora"

  engine         = "aurora-postgresql"
  engine_mode    = "provisioned"
  engine_version = "16.15"

  database_name   = "tododerechovecino"
  master_username = "tdv_admin"

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.aurora.id]

  storage_encrypted = true

  backup_retention_period = 1
  skip_final_snapshot     = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2
  }

  tags = {
    Name    = "todo-derecho-vecino-aurora"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_rds_cluster_instance" "aurora" {
  identifier         = "todo-derecho-vecino-aurora-instance"
  cluster_identifier = aws_rds_cluster.aurora.id

  instance_class = "db.serverless"
  engine         = aws_rds_cluster.aurora.engine
  engine_version = aws_rds_cluster.aurora.engine_version

  publicly_accessible = false

  tags = {
    Name    = "todo-derecho-vecino-aurora-instance"
    Project = "todo-derecho-vecino"
  }
}

output "aurora_cluster_endpoint" {
  description = "Endpoint del cluster Aurora PostgreSQL"
  value       = aws_rds_cluster.aurora.endpoint
}

output "aurora_reader_endpoint" {
  description = "Endpoint de lectura del cluster Aurora PostgreSQL"
  value       = aws_rds_cluster.aurora.reader_endpoint
}

output "aurora_port" {
  description = "Puerto PostgreSQL de Aurora"
  value       = aws_rds_cluster.aurora.port
}

output "aurora_database_name" {
  description = "Nombre de la base de datos Aurora"
  value       = aws_rds_cluster.aurora.database_name
}

output "admin_test_instance_id" {
  description = "ID de la instancia EC2 temporal de administración"
  value       = aws_instance.admin_test.id
}

output "vpc_id" {
  description = "ID de la VPC temporal"
  value       = aws_vpc.main.id
}

