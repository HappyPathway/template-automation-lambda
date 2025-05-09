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
      "echo '=== Debug: Listing directory contents ==='",
      "ls -la /tmp",
      "echo '=== Debug: Python version ==='",
      "python3 --version",
      "echo '=== Debug: Pip version ==='",
      "pip3 --version",
      
      "echo '=== Installing requirements.txt dependencies ==='",
      "pip3 install --no-cache-dir -r /tmp/requirements.txt -t /var/task -v",
      
      "echo '=== Installing pydantic explicitly ==='",
      "pip3 install --no-cache-dir 'pydantic~=2.6' -t /var/task -v",
      
      "echo '=== Installing package in development mode ==='",
      "pip3 install --no-cache-dir -e /tmp -t /var/task -v",
      
      "echo '=== Copying app.py to task root ==='",
      "cp /tmp/app.py /var/task/",
      
      "echo '=== Listing installed Python packages ==='",
      "pip3 list",
      
      "echo '=== Verifying task directory contents ==='",
      "ls -la /var/task"
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
