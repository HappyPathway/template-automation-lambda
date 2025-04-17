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