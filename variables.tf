
# Note: GitHub-specific variables (github_api, github_org_name, template_repo_name, etc.)
# have been moved to the terraform-aws-template-automation module.
# They are now configured as SSM parameters in that module.
#
# This file contains only variables related to the container image and
# ECR repository setup.

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