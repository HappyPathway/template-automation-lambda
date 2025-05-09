packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1"
    }
  }
}

variable "repository_uri" {
  type = string
}

variable "tag" {
  type    = string
  default = "latest"
}

source "docker" "lambda" {
  image  = "public.ecr.aws/lambda/python:3.11"
  commit = true
  changes = [
    "WORKDIR /var/task",
    "CMD [ \"app.lambda_handler\" ]"
  ]
}

build {
  name = "template-automation-lambda"
  
  sources = [
    "source.docker.lambda"
  ]

  # Copy the entire project directory for proper installation
  provisioner "file" {
    source      = "./"
    destination = "/tmp/"
  }

  # Use the external Python script for setup
  provisioner "shell" {
    inline = [
      "chmod +x /tmp/scripts/lambda_setup.py",
      "python3 /tmp/scripts/lambda_setup.py"
    ]
  }

  post-processors {
    post-processor "docker-tag" {
      repository = var.repository_uri
      tags       = [var.tag]
    }

    post-processor "docker-push" {
      ecr_login    = true
      login_server = var.repository_uri
    }
  }
}
