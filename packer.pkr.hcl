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

  provisioner "file" {
    source      = "./template_automation/"
    destination = "/var/task/template_automation/"
  }

  provisioner "file" {
    source      = "./app.py"
    destination = "/var/task/app.py"
  }

  provisioner "file" {
    source      = "./requirements.txt"
    destination = "/var/task/requirements.txt"
  }

  provisioner "shell" {
    inline = [
      "ls -la /var/task",  # Debug: List contents
      "pip3 install -r /var/task/requirements.txt -t /var/task"
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
