resource "aws_apigatewayv2_api" "http" {
  name          = "todo-derecho-vecino-http-api"
  protocol_type = "HTTP"
  description   = "API HTTP para consultas legales de uso de suelo en CDMX"

  tags = {
    Name    = "todo-derecho-vecino-http-api"
    Project = "todo-derecho-vecino"
  }

  cors_configuration {
    allow_origins = ["http://localhost:5500"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "consulta" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /consulta"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }

  tags = {
    Name    = "todo-derecho-vecino-default"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/POST/consulta"
}

output "api_gateway_endpoint" {
  description = "URL HTTPS de la API HTTP"
  value       = aws_apigatewayv2_api.http.api_endpoint
}
