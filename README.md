# EKS Automation Lambda

## Description

This repository contains source code and supporting files for a serverless Lambda container application.
The application uses an AWS Lambda function to process JSON input and write it to a cloned repository.
The changes are then committed and pushed to your GitHub Enterprise Server, creating a new repository
for the EKS CI/CD pipeline.

## Architecture

- AWS Lambda container image built with Packer and stored in ECR
- Infrastructure managed with Terraform
- Automated CI/CD using GitHub Actions
- Secret management using AWS Systems Manager Parameter Store

## Prerequisites

- AWS credentials with appropriate permissions
- GitHub Personal Access Token (PAT) stored in AWS Systems Manager Parameter Store
- Docker (for local development)
- Terraform
- Packer
- Python 3.11+

## Local Development

1. Clone this repository:
   ```sh
   git clone <your-github-enterprise-url>/eks-automation-lambda.git
   cd eks-automation-lambda
   ```

2. Install Python dependencies:
   ```sh
   cd eks_automation
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
  "eks_settings": {
    "attrs": {
      "account_name": "my-account",
      "aws_region": "us-east-1",
      "cluster_mailing_list": "someone@example.com",
      "cluster_name": "my-eks-cluster",
      "eks_instance_disk_size": 100,
      "eks_ng_desired_size": 2,
      "eks_ng_max_size": 10,
      "eks_ng_min_size": 2,
      "environment": "development",
      "environment_abbr": "dev",
      "organization": "my-org:my-division:my-team",
      "finops_project_name": "my_project_baseline",
      "finops_project_number": "fp00000001",
      "finops_project_role": "my_project_baseline_app",
      "vpc_domain_name": "dev.example.com",
      "vpc_name": "vpc-dev"
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
