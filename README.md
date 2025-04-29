# Template Automation Lambda

## Description

This repository contains source code and supporting files for a serverless Lambda container application.
The application uses an AWS Lambda function to process JSON input and write it to a cloned repository.
The changes are then committed and pushed to your GitHub Enterprise Server, creating a new repository
with custom configurations from your template.

## Architecture

- AWS Lambda container image built with Packer and stored in ECR 
- Infrastructure managed with Terraform
- Automated CI/CD using GitHub Actions
- Secret management using AWS Systems Manager Parameter Store

## Repository Structure

This project is split into two repositories:

1. **template-automation-lambda** (this repository)
   - Contains the Lambda function source code
   - Builds the container image with Packer
   - Publishes the image to ECR

2. **terraform-aws-template-automation**
   - Terraform module that deploys the Lambda infrastructure
   - Creates and configures all required AWS resources
   - Manages GitHub-specific configuration via SSM parameters
   - Handles permissions, API Gateway, and other infrastructure

## Prerequisites

- AWS credentials with appropriate permissions
- GitHub Personal Access Token (PAT) stored in AWS Systems Manager Parameter Store
- Docker (for local development)
- Terraform
- Packer
- Python 3.11+

## Configuration

### Lambda Configuration

The Lambda function gets its configuration from SSM Parameter Store with the following parameters:

- `/template-automation/GITHUB_API` - GitHub API URL
- `/template-automation/GITHUB_ORG_NAME` - GitHub organization name
- `/template-automation/TEMPLATE_REPO_NAME` - Name of the template repository
- `/template-automation/TEMPLATE_CONFIG_FILE` - Name of the config file (default: config.json)
- `/template-automation/GITHUB_COMMIT_AUTHOR_NAME` - Name for commit author
- `/template-automation/GITHUB_COMMIT_AUTHOR_EMAIL` - Email for commit author
- `/template-automation/TEMPLATE_TOPICS` - Comma-separated list of repository topics

### Terraform Module Configuration

These parameters are managed by the `terraform-aws-template-automation` module. When deploying
the Lambda function using the Terraform module, configure these variables in the module:

```hcl
module "template_automation" {
  source = "github.com/HappyPathway/terraform-aws-template-automation"

  # GitHub configuration
  github_api_url            = "https://api.github.com"
  github_org_name           = "your-org"
  template_repo_name        = "your-template-repo"
  
  # Other module configuration...
}
```

## Local Development

1. Clone this repository:
   ```sh
   git clone <your-github-enterprise-url>/template-automation-lambda.git
   cd template-automation-lambda
   ```

2. Install Python dependencies:
   ```sh
   cd template_automation
   pip install -r requirements.txt
   ```

3. Configure AWS credentials either through environment variables or AWS CLI profile

4. Store your GitHub PAT in AWS Systems Manager Parameter Store. The parameter name should match the
   value of `GITHUB_TOKEN_SECRET_NAME` in `eks_automation/app.py`

## Deployment

The project uses GitHub Actions for automated deployments. On push to main:

1. Creates/updates ECR repository using Terraform
2. Builds Lambda container image using Packer
3. Pushes image to ECR
4. Tags the release

For manual deployment:

1. Initialize Terraform:
   ```sh
   terraform init
   ```

2. Apply Terraform configuration:
   ```sh
   terraform apply
   ```

3. Build and push container image:
   ```sh
   packer init packer.pkr.hcl
   packer build -var "repository_uri=$(terraform output -raw repository_uri)" -var "tag=latest" packer.pkr.hcl
   ```

## Testing

The Lambda function accepts JSON input in the following format:

```json
{
  "project_name": "string",
  "template_settings": {
    "attrs": {
      "account_name": "my-account",
      "aws_region": "us-east-1",
      "team_contact": "someone@example.com",
      "project_name": "my-project",
      "environment": "development",
      "environment_abbr": "dev",
      "organization": "my-org:my-division:my-team",
      "project_id": "proj_001",
      "domain_name": "dev.example.com"
    },
    "tags": {
      "slim:schedule": "8:00-17:00"
    }
  }
}
```

### Unit Tests
To run the unit tests:
```sh
cd eks_automation
python -m pytest tests/ -v -m "not integration"
```

### Integration Tests
The integration tests require real GitHub API access. To run them:

1. Set up the required environment variables:
```sh
export GITHUB_TOKEN="your-github-token"
export GITHUB_API="https://api.github.com"  # or your GitHub Enterprise URL
export GITHUB_ORG="your-org-name"
```

2. Run the integration tests:
```sh
cd eks_automation
python -m pytest tests/ -v -m integration
```

Note: Integration tests will create temporary repositories in your GitHub organization. These repositories will be archived (not deleted) after the tests complete.

## Resources

- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [HashiCorp Packer](https://www.packer.io/docs)
- [AWS ECR Public](https://docs.aws.amazon.com/AmazonECR/latest/public/what-is-ecr.html)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
