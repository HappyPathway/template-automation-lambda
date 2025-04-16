variable "environment" {
  description = "Environment name"
  type        = string
}

variable "environment_abbr" {
  description = "Environment abbreviation"
  type        = string
}

variable "organization" {
  description = "Organization name"
  type        = string
}

variable "finops_project_name" {
  description = "FinOps project name"
  type        = string
}

variable "finops_project_number" {
  description = "FinOps project number"
  type        = string
}

variable "finops_project_role" {
  description = "FinOps project role"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs"
  type        = list(string)
}

variable "vpc_subnet_ids" {
  description = "List of VPC subnet IDs"
  type        = list(string)
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-gov-west-2"
}

variable name {
  description = "Name of the resource"
  type        = string
  default     = "eks-automation"
}

variable "lambda_deployment_type" {
  description = "Lambda deployment type: 'zip' or 'container'"
  type        = string
  default     = "zip"
  validation {
    condition     = contains(["zip", "container"], var.lambda_deployment_type)
    error_message = "Valid values for lambda_deployment_type are 'zip' or 'container'"
  }
}

variable "container_image_uri" {
  description = "ECR container image URI for Lambda container (required if lambda_deployment_type is 'container')"
  type        = string
  default     = null
}

variable "create_ecr_repository" {
  description = "Whether to create an ECR repository for Lambda container images"
  type        = bool
  default     = true
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository for Lambda container images"
  type        = string
  default     = null
}

# Environment variables for EKS Automation Lambda
variable "census_github_api" {
  description = "URL for the Census GitHub API"
  type        = string
  default     = "https://github.e.it.census.gov/api/v3"
}

variable "github_org_name" {
  description = "GitHub organization name"
  type        = string
  default     = "SCT-Engineering"
}

variable "github_token_secret_name" {
  description = "AWS SSM parameter name for the GitHub token"
  type        = string
  default     = "/eks-cluster-deployment/github_token"
}

variable "template_repo_name" {
  description = "GitHub repository name for the EKS template"
  type        = string
  default     = "template-eks-cluster"
}

variable "template_file_name" {
  description = "Template file name for the EKS configuration"
  type        = string
  default     = "eks.hcl.j2"
}

variable "hcl_file_name" {
  description = "Output file name for the rendered HCL configuration"
  type        = string
  default     = "eks.hcl"
}