terraform {
  backend "gcs" {
    bucket = "hpw-terraform-state"
    prefix = "eks-automation-lambda"
  }
}

