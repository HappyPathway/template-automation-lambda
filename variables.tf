variable "environment" {
  description = "Environment name"
  type        = string
  default     = "development"
}

variable "environment_abbr" {
  description = "Environment abbreviation"
  type        = string
  default     = "dev"
}

variable "organization" {
  description = "Organization name"
  type        = string
  default     = "census:ocio:csvd"
}

variable "finops_project_name" {
  description = "FinOps project name"
  type        = string
  default     = "csvd_platformbaseline"
}

variable "finops_project_number" {
  description = "FinOps project number"
  type        = string
  default     = "fs0000000078"
}

variable "finops_project_role" {
  description = "FinOps project role"
  type        = string
  default     = "csvd_platformbaseline_app"
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs"
  type        = list(string)
  default     = ["sg-03cbf2a626ed55c7e"]
}

variable "vpc_subnet_ids" {
  description = "List of VPC subnet IDs"
  type        = list(string)
  default     = ["subnet-05192178ac094f639", "subnet-022370a5a03585376"]
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}
