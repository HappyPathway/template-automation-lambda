# IAM Role for CodeBuild
resource "aws_iam_role" "codebuild" {
  name = "template-automation-lambda-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Role Policy for CodeBuild
resource "aws_iam_role_policy" "codebuild" {
  name = "template-automation-lambda-codebuild-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Resource = ["*"]
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
      },
      {
        Effect = "Allow"
        Resource = ["*"]
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "codebuild:StartBuild",
          "codebuild:BatchGetBuilds",
          "codebuild:StopBuild"
        ]
      },
          "ecr:CompleteLayerUpload"
        ]
      }
    ]
  })
}

# CodeBuild Project
resource "aws_codebuild_project" "lambda_builder" {
  name          = "eks-automation-lambda-builder"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = "30"

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                      = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                       = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode            = true

    environment_variable {
      name  = "REPOSITORY_URI"
      value = var.repository_uri
    }
  }

  source {
    type            = "GITHUB"
    location        = var.github_repo_url
    git_clone_depth = 1
    buildspec       = "buildspec.yml"
  }

  cache {
    type = "NO_CACHE"
  }

  logs_config {
    cloudwatch_logs {
      status = "ENABLED"
    }
  }
}
