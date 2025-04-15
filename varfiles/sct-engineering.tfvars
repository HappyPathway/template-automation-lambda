environment           = "development"
environment_abbr      = "dev"
organization          = "census:ocio:csvd"
finops_project_name   = "csvd_platformbaseline"
finops_project_number = "fs0000000078"
finops_project_role   = "csvd_platformbaseline_app"
vpc_security_group_ids = [
  "sg-0641c697588b9aa6b",
  "sg-0cc69de0fa6f337c5"
]
vpc_subnet_ids = [
  "subnet-062189d742937204e"
]
lambda_timeout = 30
aws_region     = "us-gov-west-1"
