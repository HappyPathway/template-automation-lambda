variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-west-2"
}

variable "repository_uri" {
  description = "The URI of the ECR repository where the Lambda image will be pushed"
  type        = string
}

variable "github_repo_url" {
  description = "The HTTPS clone URL of the GitHub repository"
  type        = string
}
