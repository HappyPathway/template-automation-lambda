aws_region     = "us-east-1"
repository_name = "template-automation-lambda"

catalog_data = {
  about_text        = "Template Automation Lambda Image"
  architectures     = ["x86_64"]
  description       = "Lambda container image for template automation"
  operating_systems = ["AmazonLinux2"]
  usage_text        = "Creates a Template Automation Lambda container image"
}

tags = {
  env         = "production"
  managed_by  = "terraform"
  project     = "template-automation"
}
