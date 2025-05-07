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

  provisioner "shell" {
    inline = [
      "ls -la /tmp",  # Debug: List contents of tmp directory
      "pip3 install -r /tmp/requirements.txt -t /var/task",
      "pip3 install /tmp -t /var/task",  # Install the package itself
      "cp /tmp/app.py /var/task/",  # Copy the entry point file
      "ls -la /var/task"  # Debug: List contents of task directory
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
