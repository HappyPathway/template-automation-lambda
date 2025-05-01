terraform {
  backend "gcs" {
    bucket = "hpw-terraform-state"
    prefix = "template-automation-lambda"
  }
}
