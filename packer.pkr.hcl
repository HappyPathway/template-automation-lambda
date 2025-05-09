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
      
      "echo '=== Installing dependencies from requirements.txt ==='",
      "pip3 install --no-cache-dir -r /tmp/requirements.txt -t /var/task -v",
      
      "echo '=== Installing package in development mode ==='",
      "pip3 install --no-cache-dir -e /tmp -t /var/task -v",
      
      "echo '=== Copying app.py to task root ==='",
      "cp /tmp/app.py /var/task/",
      
      "echo '=== Explicitly copying template_automation package directory ==='",
      "cp -r /tmp/template_automation /var/task/",
      
      "echo '=== Verifying dependencies installation ==='",
      "python3 -c \"import sys; print(sys.path)\"",
      "python3 -c \"import jinja2; print(f'jinja2 version: {jinja2.__version__}')\" || echo 'jinja2 not installed correctly'",
      "python3 -c \"import github; print(f'PyGithub version: {github.__version__}')\" || echo 'PyGithub not installed correctly'",
      "python3 -c \"import pydantic; print(f'pydantic version: {pydantic.__version__}')\" || echo 'pydantic not installed correctly'",
      "python3 -c \"import boto3; print(f'boto3 version: {boto3.__version__}')\" || echo 'boto3 not installed correctly'",
      "python3 -c \"import template_automation; print('template_automation package found')\" || echo 'template_automation not installed correctly'",
      
      "echo '=== Listing installed Python packages ==='",
      "pip3 list",
      
      "echo '=== Verifying task directory contents ==='",
      "ls -la /var/task",
      "ls -la /var/task/template_automation"
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
