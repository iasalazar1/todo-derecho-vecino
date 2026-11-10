# Bucket privado para alojar los archivos estáticos del frontend.
resource "aws_s3_bucket" "frontend" {
  bucket = "todo-derecho-vecino-frontend-${data.aws_caller_identity.current.account_id}-${var.aws_region}"

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name    = "todo-derecho-vecino-frontend"
    Project = "todo-derecho-vecino"
  }
}

# Bloqueo total del acceso público.
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Cifrado de los archivos almacenados.
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Control de versiones para facilitar la recuperación de archivos.
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Deshabilita las ACL y mantiene el control de propiedad en la cuenta.
resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
