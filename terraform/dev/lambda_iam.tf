# ============================================================
# Semana 7 - IAM para AWS Lambda
# ============================================================

data "aws_caller_identity" "current" {}

# ------------------------------------------------------------
# Rol de ejecución de Lambda
# ------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "TodoDerechoVecino-Lambda-Execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "TodoDerechoVecino-Lambda-Execution"
    Project = "todo-derecho-vecino"
  }
}

# Permisos de acceso VPC y CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ------------------------------------------------------------
# Política de acceso a Bedrock y Secrets Manager
# ------------------------------------------------------------

resource "aws_iam_role_policy" "lambda_application" {
  name = "TodoDerechoVecino-Lambda-Application"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "InvokeTitanEmbeddings"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
        ]
      },
      {
        Sid    = "InvokeClaudeInferenceProfile"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-sonnet-4-6"
        ]
      },
      {
        Sid    = "InvokeClaudeFoundationModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6",
          "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-6",
          "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-6"
        ]
      },
      {
        Sid    = "ReadAuroraSecret"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_rds_cluster.aurora.master_user_secret[0].secret_arn
        ]
      }
    ]
  })
}
