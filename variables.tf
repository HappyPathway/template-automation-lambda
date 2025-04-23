variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "repository_name" {
  description = "Name of the ECR public repository"
  type        = string
  default     = "template-automation-lambda"
}

variable "environment" {
  description = "Environment tag value"
  type        = string
  default     = "production"
}

variable "github_api" {
  description = "URL for the GitHub Enterprise API"
  type        = string
  default     = "https://github.enterprise.example.com/api/v3"
}

variable "github_org_name" {
  description = "GitHub organization name"
  type        = string
  default     = "your-org"
}

variable "github_token_secret_name" {
  description = "AWS SSM parameter name for the GitHub token"
  type        = string
  default     = "/github/token"
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

variable "catalog_data" {
  description = "Configuration for the ECR repository catalog data"
  type = object({
    about_text        = string
    architectures     = list(string)
    description       = string
    operating_systems = list(string)
    usage_text       = string
  })
  default = {
    about_text        = "Template Automation Lambda Image"
    architectures     = ["x86_64"]
    description       = "Lambda container image for template automation"
    operating_systems = ["AmazonLinux2"]
    usage_text        = "Creates a Template Automation Lambda container image"
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    env = "production"
  }
}