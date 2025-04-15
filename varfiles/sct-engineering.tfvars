name = "eks-repo-automation"
# This file contains the variable values for the Terraform configuration.
# It is used to set up the AWS Lambda function and its associated resources.
# The values here are specific to the development environment and should be
# adjusted for production or other environments as needed.
#
# Environment variables
# These variables are used to configure the AWS Lambda function and its
# associated resources. They include the environment name, organization,
# FinOps project details, VPC security group IDs, subnet IDs, and Lambda
# timeout settings.
# The AWS region is set to "us-gov-west-1" for the development environment.
# The VPC security group IDs and subnet IDs are specific to the AWS
# infrastructure setup and should be verified before deployment.
# The Lambda timeout is set to 30 seconds, which should be sufficient for
# most operations. 
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
