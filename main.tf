# 
# This Terraform configuration creates only the ECR repository for the container image.
# The Lambda function, API Gateway, IAM roles, and other infrastructure are managed by 
# the terraform-aws-template-automation module.

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

resource "aws_ecrpublic_repository" "ecr_repo" {
  repository_name = var.repository_name

  catalog_data {
    about_text        = var.catalog_data.about_text
    architectures     = var.catalog_data.architectures
    description       = var.catalog_data.description
    operating_systems = var.catalog_data.operating_systems
    usage_text        = var.catalog_data.usage_text
  }

  tags = var.tags
}

locals {
  repository_uri = aws_ecrpublic_repository.ecr_repo.repository_uri
  repository_id  = aws_ecrpublic_repository.ecr_repo.id
  aws_account_id = data.aws_caller_identity.current.account_id
  region         = var.aws_region
  arn            = aws_ecrpublic_repository.ecr_repo.arn
}

output "repository_uri" {
  description = "The URI of the ECR repository"
  value       = local.repository_uri
}

output "repository_id" {
  description = "The ID of the ECR repository"
  value       = local.repository_id
}

output "aws_account_id" {
  description = "The ID of the AWS account"
  value       = local.aws_account_id
}

output "region" {
  description = "The AWS region where resources are created"
  value       = local.region
}

output "arn" {
  description = "The ARN of the ECR repository"
  value       = local.arn
}