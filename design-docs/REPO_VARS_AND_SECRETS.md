# Repository Variables and Secrets Management

This document outlines the approach for managing GitHub Actions secrets and variables for newly created repositories using AWS Parameter Store and Secrets Manager.

## Overview

The template automation system will configure GitHub Actions secrets and variables by:
1. Reading secrets from AWS Secrets Manager
2. Reading variables from AWS Parameter Store
3. Setting them in the newly created repository using GitHub's API

## Implementation

### Parameter Structure

#### AWS Parameter Store
```
/template-automation/
  ├── variables/
  │   ├── global/                    # Variables for all repos
  │   │   ├── AWS_REGION
  │   │   └── TERRAFORM_VERSION
  │   └── by-type/                   # Variables by repository type
  │       ├── eks-cluster/
  │       │   ├── CLUSTER_VERSION
  │       │   └── NODE_TYPE
  │       └── terraform-module/
  │           ├── GO_VERSION
  │           └── TFLINT_VERSION
```

#### AWS Secrets Manager
```
template-automation/
  ├── secrets/global/               # Secrets for all repos
  │   ├── AWS_ACCESS_KEY_ID
  │   └── AWS_SECRET_ACCESS_KEY
  └── secrets/by-type/             # Secrets by repository type
      ├── eks-cluster/
      │   └── KUBECONFIG
      └── terraform-module/
          └── SNYK_TOKEN
```

### Infrastructure Changes

#### Lambda Configuration

Add environment variables to the Lambda function:

```hcl
# In terraform-aws-template-automation/main.tf
resource "aws_lambda_function" "template_automation" {
  # ...existing configuration...
  
  environment {
    variables = {
      PARAM_STORE_PREFIX = "/template-automation"
      SECRETS_PREFIX = "template-automation"
    }
  }
}
```

#### IAM Permissions

Add required permissions to the Lambda role:

```hcl
# In terraform-aws-template-automation/iam.tf
data "aws_iam_policy_document" "secrets_access" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:ListSecrets"
    ]
    resources = [
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.secrets_prefix}/*"
    ]
  }
}

data "aws_iam_policy_document" "ssm_access" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath"
    ]
    resources = [
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${var.param_store_prefix}/*"
    ]
  }
}
```

### Implementation Details

#### In GitHubClient

The `GitHubClient` class will be extended with methods to handle secrets and variables:

```python
class GitHubClient:
    def set_repository_secrets(self, repo_name: str, repo_type: str = None) -> None:
        """Set GitHub Actions secrets for a repository."""
        # Get global secrets
        secrets = self._get_aws_secrets("secrets/global")
        
        # Get type-specific secrets
        if repo_type:
            type_secrets = self._get_aws_secrets(f"secrets/by-type/{repo_type}")
            secrets.update(type_secrets)
            
        # Set secrets in repository
        repo = self.org.get_repo(repo_name)
        for name, value in secrets.items():
            repo.create_secret(name, value)
    
    def set_repository_variables(self, repo_name: str, repo_type: str = None) -> None:
        """Set GitHub Actions variables for a repository."""
        # Get global variables
        variables = self._get_ssm_parameters("variables/global")
        
        # Get type-specific variables
        if repo_type:
            type_vars = self._get_ssm_parameters(f"variables/by-type/{repo_type}")
            variables.update(type_vars)
            
        # Set variables in repository
        repo = self.org.get_repo(repo_name)
        for name, value in variables.items():
            repo.create_variable(name, value)
```

#### In Lambda Handler

The handler will be updated to set secrets and variables during repository creation:

```python
def lambda_handler(event: dict, context) -> dict:
    # ...existing initialization code...
    
    # Create repository
    repo = github.get_repository(repo_name, create=True)
    
    # Set secrets and variables
    repo_type = template_input.template_settings.get("type")
    github.set_repository_secrets(repo_name, repo_type)
    github.set_repository_variables(repo_name, repo_type)
    
    # ...rest of handler code...
```

## Security Considerations

1. **Secret Encryption**: All secrets are encrypted at rest in AWS
2. **IAM Access Control**: Fine-grained control over who can access secrets
3. **Audit Trail**: AWS CloudTrail tracks all secret access
4. **Repository Isolation**: Each repository gets its own copy of secrets
5. **Least Privilege**: Lambda has minimal required permissions

## Usage Examples

### Setting Up Repository Type Secrets

1. Store secrets in AWS:
```bash
aws secretsmanager create-secret \
  --name "template-automation/secrets/by-type/eks-cluster/KUBECONFIG" \
  --secret-string "..." 
```

2. Store variables in Parameter Store:
```bash
aws ssm put-parameter \
  --name "/template-automation/variables/by-type/eks-cluster/CLUSTER_VERSION" \
  --value "1.27" \
  --type "String"
```

### Creating a Repository with Secrets

Create a new EKS cluster repository with the Lambda function:

```json
{
    "action": "create",
    "project_name": "production-eks",
    "template_settings": {
        "type": "eks-cluster",
        "environment": "production"
    }
}
```

The Lambda function will:
1. Create the repository
2. Generate a secure destroy token
3. Store the token in a `.destroy-token` file in the repository root
4. Set up global secrets and variables
5. Set up EKS-specific secrets and variables
6. Configure necessary GitHub Actions environment

The response will include the repository URL:

```json
{
    "status": "success",
    "repository_url": "https://github.com/org/production-eks",
    "message": "Repository created successfully. The destroy token is stored in .destroy-token file."
}
```

**Important**: The destroy token is stored in the `.destroy-token` file in your repository. You'll need this token to delete the repository later. The file looks like:

```plaintext
# This file contains the token required to delete this repository.
# Store this token securely as it will be required for repository deletion.
# DO NOT delete or modify this file unless you want to prevent repository deletion.

ESxK2ld9J4mCpA-ghi8932jk...
```

### Destroying a Repository

To clean up a repository and its associated secrets/variables:

```json
{
    "action": "destroy",
    "project_name": "production-eks",
    "destroy_token": "ESxK2ld9J4mCpA-ghi8932jk..."
}
```

The Lambda function will:
1. Validate the provided destroy token
2. Delete all repository secrets
3. Delete all repository variables
4. Delete the repository itself

If an invalid destroy token is provided, the operation will fail with an error.

## Future Enhancements

1. **Secret Rotation**: Implement automatic secret rotation
2. **Environment Support**: Add environment-specific secrets (dev/staging/prod)
3. **Organization Variables**: Support for organization-level variables
4. **Validation Rules**: Add validation for secret/variable names and values
5. **Backup/Restore**: Implement backup and restore for secrets/variables
