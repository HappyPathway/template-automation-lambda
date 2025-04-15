# API Gateway
resource "aws_api_gateway_rest_api" "eks_automation" {
  name = "eks-automation-api"
  tags = local.common_tags
}

resource "aws_api_gateway_resource" "eks_automation" {
  rest_api_id = aws_api_gateway_rest_api.eks_automation.id
  parent_id   = aws_api_gateway_rest_api.eks_automation.root_resource_id
  path_part   = "EKSAutomation"
}

resource "aws_api_gateway_method" "eks_automation" {
  rest_api_id      = aws_api_gateway_rest_api.eks_automation.id
  resource_id      = aws_api_gateway_resource.eks_automation.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.eks_automation.id
  resource_id             = aws_api_gateway_resource.eks_automation.id
  http_method             = aws_api_gateway_method.eks_automation.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.eks_automation.invoke_arn
}

resource "aws_api_gateway_deployment" "eks_automation" {
  rest_api_id = aws_api_gateway_rest_api.eks_automation.id
  depends_on  = [aws_api_gateway_integration.lambda]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.eks_automation.id
  rest_api_id   = aws_api_gateway_rest_api.eks_automation.id
  stage_name    = "Prod"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.eks_automation.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.eks_automation.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options" {
  rest_api_id   = aws_api_gateway_rest_api.eks_automation.id
  resource_id   = aws_api_gateway_resource.eks_automation.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options" {
  rest_api_id = aws_api_gateway_rest_api.eks_automation.id
  resource_id = aws_api_gateway_resource.eks_automation.id
  http_method = aws_api_gateway_method.options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.eks_automation.id
  resource_id = aws_api_gateway_resource.eks_automation.id
  http_method = aws_api_gateway_method.options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.eks_automation.id
  resource_id = aws_api_gateway_resource.eks_automation.id
  http_method = aws_api_gateway_method.options.http_method
  status_code = aws_api_gateway_method_response.options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'",
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_usage_plan" "eks_automation" {
  name        = "eks-automation-usage-plan"
  description = "Usage plan for EKS Automation API"

  api_stages {
    api_id = aws_api_gateway_rest_api.eks_automation.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  quota_settings {
    limit  = 5000
    period = "MONTH"
  }

  throttle_settings {
    burst_limit = 500
    rate_limit  = 100
  }

  tags = local.common_tags
}

resource "aws_api_gateway_api_key" "eks_automation" {
  name = "eks-automation-api-key"
}

resource "aws_api_gateway_usage_plan_key" "eks_automation" {
  key_id        = aws_api_gateway_api_key.eks_automation.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.eks_automation.id
}

# Lambda Layer
resource "aws_lambda_layer_version" "git" {
  filename            = "layer.zip" # Make sure to create this zip file with Git binaries
  layer_name          = "git-lambda-layer"
  description         = "Git Lambda Layer"
  compatible_runtimes = ["python3.9", "python3.10", "python3.11"]
}

# Lambda Function
resource "aws_lambda_function" "eks_automation" {
  filename      = "eks_automation.zip" # Make sure to create this zip file
  function_name = "eks-automation"
  role          = aws_iam_role.lambda_role.arn
  handler       = "app.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.lambda_timeout

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  layers = [aws_lambda_layer_version.git.arn]

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  tags = local.common_tags
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "eks-automation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policies
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ssm_access" {
  name = "eks-automation-ssm-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SSMDescribeParametersPolicy"
        Effect   = "Allow"
        Action   = ["ssm:DescribeParameters"]
        Resource = "*"
      },
      {
        Sid    = "SSMGetParameterPolicy"
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = "*"
      }
    ]
  })
}
