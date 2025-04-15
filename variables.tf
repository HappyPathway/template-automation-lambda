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