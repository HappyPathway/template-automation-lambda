# EKS Automation Lambda Implementation Plan

## Project Map

### template-eks-cluster
This is the template repo that is generated from the lambda function, we're designing this whole system to be agnostic towards which repos it's creating; this will be the first example of this style of condiguration (pattern).

### terraform-aws-template-automation
This is the terraform module that is repsonsible for deploying our Lambda function along with any peripheral infrastructure that may be required, such as API Gateway. If SSM parameters or Secrets are required in the lambda function, they get deployed through this module.

### template-automation-lambda
This is actual Lambda function, this repo creates a Docker image that we deploy to Lambda. Our actual lambda code is in template_automation/app.py.

### Build Infrastructure Requirements
The Terraform configuration in this repository is specifically for building the Lambda container image in ECR. Due to tooling restrictions and access requirements, the build process must be executed in GitHub.com rather than in the target organization's environment. This means:

- The container image build pipeline runs in GitHub.com
- Terraform in this repo manages only build-related resources (ECR repository, build IAM roles)
- The build process cannot access internal tools or resources of the target organization
- The resulting container image is then referenced by the terraform-aws-template-automation module for actual deployment

## Overview
This document outlines the implementation plan for enhancing the EKS Automation Lambda to improve its GitHub integration workflow and testing capabilities. Most of this work will take place in template_automation/app.py

## Implementation Phases

### Phase 1: Lambda Function Updates
Updates to the Lambda function to improve repository management:

- **Branch Management**
  - Create new "init-cluster" branch instead of pushing directly to main
  - Implement branch creation in GitHub client (template_automation/app.py)
  - Add error handling for branch operations

- **Pull Request Automation**
  - Add automatic PR creation after pushing changes
  - Include standard PR template and description
  - Implement PR creation in GitHub client

### Phase 2: GitHub Actions Workflow Updates
Clean out current github actions in template repo (template-eks-cluster).
Enhance the GitHub Actions workflow configuration:

- **HCL File Generation**
  - Add action to expand config.js into HCL files, this will be done through ansible. Review the generate_hcl_files.yml playbook.
  - Implement Terraform plan action post-HCL generation
  - Add validation steps for generated HCL

- **Runner Configuration**
  - Templateize GitHub Actions workflow files
  - Configure runners based on AWS account IDs
  - Add support for lab environment runners
  - Implement account-specific runner selection

### Phase 3: Testing Implementation
Comprehensive testing setup:

- **Lab Environment**
  - Configure workflow for lab AWS account
  - Set up isolated testing environment
  - Create test cluster configurations

- **End-to-End Testing**
  - Implement full workflow testing
  - Create demonstration environment
  - Add integration tests for GitHub operations
  - Implement validation checks

### Phase 4: Manual Trigger Interface
Short-term manual operation support:

- **Documentation**
  - Lambda invocation process
  - Example payload templates
  - Verification steps and checks

- **Future Considerations**
  - CRF integration planning
  - Automation transition strategy

## Success Criteria
- Lambda successfully creates branches and PRs
- GitHub Actions properly expand config and run Terraform plans
- Workflows correctly target different AWS accounts
- End-to-end testing works in lab environment
- Clear documentation exists for manual processes

## Dependencies
- GitHub API access and permissions
- AWS account access for testing
- Runner configurations for different environments
