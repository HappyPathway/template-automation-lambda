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
    "CMD [ \"app.handler\" ]"
  ]
}

build {
  name = "eks-automation-lambda"
  
  sources = [
    "source.docker.lambda"
  ]

  provisioner "file" {
    source      = "./eks_automation"
    destination = "/var/task"
  }

  provisioner "shell" {
    inline = [
      "cd /var/task",
      "pip3 install -r requirements.txt -t ."
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