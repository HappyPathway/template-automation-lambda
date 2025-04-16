# API Gateway HTTP API without CORS (we'll add CORS separately)
resource "aws_apigatewayv2_api" "lambda_api" {
  name          = "${var.name}-api-gateway"
  protocol_type = "HTTP"
  cors_configuration {
        allow_credentials = false
        allow_headers     = [
            "*",
        ]
        allow_methods     = [
            "POST",
        ]
        allow_origins     = [
            "*",
        ]
        expose_headers    = [
            "*",
        ]
        max_age           = 86400
    }
  lifecycle {
    ignore_changes = [
        cors_configuration
    ]
  }
}

# API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.lambda_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.eks_automation.invoke_arn
  payload_format_version = "2.0"
}

# API Gateway Route for POST requests
resource "aws_apigatewayv2_route" "lambda_route" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "lambda_stage" {
  api_id      = aws_apigatewayv2_api.lambda_api.id
  name        = "$default"
  auto_deploy = true
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.eks_automation.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}

# Add API Gateway URL to outputs
output "api_gateway_invoke_url" {
  value       = "${aws_apigatewayv2_stage.lambda_stage.invoke_url}"
  description = "API Gateway URL for invoking the Lambda function"
}
