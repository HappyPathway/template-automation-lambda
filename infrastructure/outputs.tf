output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = aws_codebuild_project.lambda_builder.name
}

output "codebuild_project_arn" {
  description = "ARN of the CodeBuild project"
  value       = aws_codebuild_project.lambda_builder.arn
}

output "iam_role_arn" {
  description = "ARN of the IAM role used by CodeBuild"
  value       = aws_iam_role.codebuild.arn
}
