locals {
  lambda_zip_path = abspath("${path.module}/../../build/lambda-deployment.zip")
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/todo-derecho-vecino-api"
  retention_in_days = 14

  tags = {
    Name    = "todo-derecho-vecino-api"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_lambda_function" "api" {
  function_name = "todo-derecho-vecino-api"
  description   = "Agente legal de consultas de uso de suelo CDMX"
  role          = aws_iam_role.lambda_execution.arn

  filename         = local.lambda_zip_path
  source_code_hash = filebase64sha256(local.lambda_zip_path)

  runtime       = "python3.12"
  architectures = ["x86_64"]
  handler       = "lambda_function.lambda_handler"

  memory_size = 512
  timeout     = 28

  vpc_config {
    subnet_ids = [
      aws_subnet.private_a.id,
      aws_subnet.private_b.id
    ]

    security_group_ids = [
      aws_security_group.lambda.id
    ]
  }

  environment {
    variables = {
      DB_HOST          = "todo-derecho-vecino-aurora.cluster-cmh6wme8kwix.us-east-1.rds.amazonaws.com"
      DB_PORT          = "5432"
      DB_NAME          = "tododerechovecino"
      DB_SECRET_ARN    = "arn:aws:secretsmanager:us-east-1:857385469837:secret:rds!cluster-db1d83e4-6048-4943-9dc6-83c4c6d3dc8d-EbTCxN"
      BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
    }
  }


  depends_on = [
    aws_iam_role_policy.lambda_application,
    aws_iam_role_policy_attachment.lambda_vpc_execution,
    aws_cloudwatch_log_group.lambda
  ]

  tags = {
    Name    = "todo-derecho-vecino-api"
    Project = "todo-derecho-vecino"
  }
}
