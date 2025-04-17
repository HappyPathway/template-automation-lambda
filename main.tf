provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

resource "aws_ecrpublic_repository" "eks-automation-lambda" {
  repository_name = "eks-automation-lambda"

  catalog_data {
    about_text        = "EKS Automation Lambda Image"
    architectures     = ["x86_64"]
    description       = "Lambda container image for EKS automation"
    operating_systems = ["AmazonLinux2"]
    usage_text        = "Creates an EKS Automation Lambda container image"
  }

  tags = {
    env = "production"
  }
}

locals {
  repository_uri = aws_ecrpublic_repository.eks-automation-lambda.repository_uri
  repository_id  = aws_ecrpublic_repository.eks-automation-lambda.id
  aws_account_id = data.aws_caller_identity.current.account_id
  region         = "us-east-1"
  arn            = aws_ecrpublic_repository.eks-automation-lambda.arn
}

output "repository_uri" {
  value = local.repository_uri
}

output "repository_id" {
  value = local.repository_id
}

output "aws_account_id" {
  value = local.aws_account_id
}

output "region" {
  value = local.region
}

output "arn" {
  value = local.arn
}