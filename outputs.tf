output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.prod.invoke_url}${aws_api_gateway_resource.eks_automation.path}"
}

output "api_key" {
  description = "API Key for accessing the endpoint"
  value       = aws_api_gateway_api_key.eks_automation.value
  sensitive   = true
}
