# S3 Bucket for Lambda artifacts - Only needed for zip deployments
resource "aws_s3_bucket" "lambda_artifacts" {
  count  = var.lambda_deployment_type == "zip" ? 1 : 0
  
  bucket = "${var.name}-lambda-artifacts-${data.aws_caller_identity.current.account_id}"
  
  tags = local.common_tags

  # Package Lambda function and layer
  provisioner "local-exec" {
    command = "${path.module}/scripts/package_lambda.py ${path.module}"
    environment = {
      PIP_CONFIG_FILE = "${path.module}/scripts/pip.conf"
    }
  }
}

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Upload Lambda package to S3 - Only for zip deployments
resource "aws_s3_object" "lambda_package" {
  count  = var.lambda_deployment_type == "zip" ? 1 : 0
  
  bucket = aws_s3_bucket.lambda_artifacts[0].id
  key    = "eks_automation.zip"
  source = "${path.module}/dist/eks_automation.zip"
  depends_on = [aws_s3_bucket.lambda_artifacts]
}

# Upload Lambda layer to S3 - Only for zip deployments
resource "aws_s3_object" "lambda_layer" {
  count  = var.lambda_deployment_type == "zip" ? 1 : 0
  
  bucket = aws_s3_bucket.lambda_artifacts[0].id
  key    = "layer.zip"
  source = "${path.module}/dist/layer.zip"
  depends_on = [aws_s3_bucket.lambda_artifacts]
}

# Lambda Function URL feature is not available or not working properly in AWS GovCloud
# Using API Gateway as an alternative (defined in api_gateway.tf)

# Lambda Layer - Only used for zip deployments
resource "aws_lambda_layer_version" "git" {
  count            = var.lambda_deployment_type == "zip" ? 1 : 0
  
  s3_bucket        = aws_s3_bucket.lambda_artifacts.id
  s3_key           = "layer.zip"
  layer_name       = "${var.name}-lambda-layer"
  description      = "${var.name} Lambda Layer"
  compatible_runtimes = ["python3.9", "python3.10", "python3.11"]
  depends_on = [aws_s3_object.lambda_layer]
}

# Lambda Function
resource "aws_lambda_function" "eks_automation" {
  function_name    = "${var.name}-eks-automation"
  role             = aws_iam_role.lambda_role.arn
  timeout          = var.lambda_timeout
  
  # Conditional deployment based on deployment type
  dynamic "image_config" {
    for_each = var.lambda_deployment_type == "container" ? [1] : []
    content {
      command = ["app.lambda_handler"]
    }
  }
  
  # Set package type based on deployment method
  package_type = var.lambda_deployment_type == "container" ? "Image" : "Zip"
  
  # Container image configuration
  image_uri = var.lambda_deployment_type == "container" ? var.container_image_uri : null
  
  # Zip deployment configuration
  s3_bucket = var.lambda_deployment_type == "zip" ? aws_s3_bucket.lambda_artifacts[0].id : null
  s3_key    = var.lambda_deployment_type == "zip" ? "eks_automation.zip" : null
  handler   = var.lambda_deployment_type == "zip" ? "app.lambda_handler" : null
  runtime   = var.lambda_deployment_type == "zip" ? "python3.9" : null
  layers    = var.lambda_deployment_type == "zip" ? [aws_lambda_layer_version.git[0].arn] : null

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  environment {
    variables = {
      ENVIRONMENT = var.environment
      CENSUS_GITHUB_API       = "https://github-instance.your-domain.com/api/v3"
      GITHUB_ORG_NAME         = "Your-Organization"
      GITHUB_TOKEN_SECRET_NAME = "/path/to/github/token"
      TEMPLATE_REPO_NAME      = "your-template-repo"
      TEMPLATE_FILE_NAME      = "template.j2"
      HCL_FILE_NAME           = "config.hcl"
    }
  }

  tags = local.common_tags
  depends_on = concat(
    [
      aws_iam_role_policy_attachment.lambda_vpc_access,
      aws_iam_role_policy.lambda_ssm_access,
    ],
    var.lambda_deployment_type == "zip" ? [
      aws_s3_object.lambda_package,
      aws_s3_object.lambda_layer
    ] : []
  )
}

# CloudWatch Log Group for Lambda Function
resource "aws_cloudwatch_log_group" "eks_automation" {
  name              = "/aws/lambda/${aws_lambda_function.eks_automation.function_name}"
  retention_in_days = 14 # Or your desired retention period

  tags = local.common_tags
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.name}-lambda-role"

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
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ssm_access" {
  name = "${var.name}-ssm-access"
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

resource "aws_iam_role_policy" "lambda_function_url" {
  name = "${var.name}-function-url-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:CreateFunctionUrlConfig",
          "lambda:UpdateFunctionUrlConfig",
          "lambda:DeleteFunctionUrlConfig",
          "lambda:GetFunctionUrlConfig",
          "lambda:InvokeFunctionUrl",
          "lambda:AddPermission",
          "lambda:RemovePermission"
        ]
        Resource = [
          aws_lambda_function.eks_automation.arn,
          "${aws_lambda_function.eks_automation.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.eks_automation.arn
      }
    ]
  })
}

# ECR Repository for Lambda container images
resource "aws_ecr_repository" "lambda_container" {
  count = var.lambda_deployment_type == "container" && var.create_ecr_repository ? 1 : 0
  
  name                 = coalesce(var.ecr_repository_name, "${var.name}-lambda-container")
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = local.common_tags
}

# ECR Repository Policy
resource "aws_ecr_repository_policy" "lambda_container_policy" {
  count = var.lambda_deployment_type == "container" && var.create_ecr_repository ? 1 : 0
  
  repository = aws_ecr_repository.lambda_container[0].name
  policy     = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}
