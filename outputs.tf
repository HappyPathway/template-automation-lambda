# output "function_url" {
#   description = "API Gateway URL for invoking the Lambda function"
#   value       = aws_apigatewayv2_stage.lambda_stage.invoke_url
# }

# output "function_arn" {
#   description = "Lambda function ARN"
#   value       = aws_lambda_function.eks_automation.arn
# }

output user {
  value = data.aws_caller_identity.current
}

output log_group {
  value = aws_cloudwatch_log_group.eks_automation.name
}

output aws_region {
  value = data.aws_region.current.name
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda Function"
  value       = aws_lambda_function.eks_automation.arn
}

output "lambda_function_name" {
  description = "The name of the Lambda Function"
  value       = aws_lambda_function.eks_automation.function_name
}

output "lambda_deployment_type" {
  description = "The deployment type used for the Lambda function (zip or container)"
  value       = var.lambda_deployment_type
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository (only applicable when using container deployment)"
  value       = var.lambda_deployment_type == "container" && var.create_ecr_repository ? aws_ecr_repository.lambda_container[0].repository_url : null
}

output "container_image_uri" {
  description = "The container image URI used for the Lambda function (only applicable when using container deployment)"
  value       = var.lambda_deployment_type == "container" ? var.container_image_uri : null
}