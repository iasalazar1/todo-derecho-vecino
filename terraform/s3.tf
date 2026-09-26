resource "aws_s3_bucket" "legal_documents" {
  bucket = "todo-derecho-vecino-${data.aws_caller_identity.current.account_id}-${var.aws_region}"

  tags = {
    Name    = "todo-derecho-vecino-legal-documents"
    Project = "todo-derecho-vecino"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "legal_documents" {
  bucket = aws_s3_bucket.legal_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "legal_documents" {
  bucket = aws_s3_bucket.legal_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "legal_documents" {
  bucket = aws_s3_bucket.legal_documents.id

  versioning_configuration {
    status = "Enabled"
  }
}
