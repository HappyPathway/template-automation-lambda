terraform {
  backend "gcs" {
    bucket = "hpwe-terraform-state"
    prefix = "eks-automation-lambda"
  }
}

