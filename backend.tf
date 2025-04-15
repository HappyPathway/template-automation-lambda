terraform {
  backend "s3" {
    bucket         = "inf-tfstate-us-gov-west-1-229685449397"
    key            = "csvd-dev-gov/common/apps/eks-automation/terraform.tfstate"
    region         = "us-gov-west-1"
    dynamodb_table = "tf_remote_state"
  }
}
