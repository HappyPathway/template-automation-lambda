
locals {
  common_tags = {
    environment           = var.environment
    environment_abbr      = var.environment_abbr
    organization          = var.organization
    finops_project_name   = var.finops_project_name
    finops_project_number = var.finops_project_number
    finops_project_role   = var.finops_project_role
  }
}