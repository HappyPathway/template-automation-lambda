# Template Automation System Implementation Plan

## System Architecture

The Template Automation System is designed to be a generic, template-agnostic infrastructure that can automate the creation and configuration of any type of repository from a template. The system consists of two core components and can work with any number of template repositories.

### Core Components

#### terraform-aws-template-automation
This is the foundational Terraform module that deploys the automation infrastructure:
- Deploys the Lambda function and required AWS resources (API Gateway, IAM roles, etc.)
- Manages any required SSM parameters or Secrets
- Provides a reusable module that can be included in any AWS environment
- Template-agnostic - works with any type of repository template

#### template-automation-lambda
This is the engine of the automation system:
- Implements the core repository templating logic in template_automation/app.py
- Packaged as a Docker image for Lambda deployment
- Handles repository creation, branch management, and PR automation
- Template-agnostic - can work with any properly structured template repository

### Template Repositories

#### template-eks-cluster (Example)
This is an example template repository that demonstrates how to structure a template for use with the automation system:
- Shows the pattern for creating EKS clusters
- Serves as a reference implementation
- Demonstrates best practices for template structure
- One of many possible templates that could be used with the system

### Build Infrastructure Requirements
The Terraform configuration in this repository is specifically for building the Lambda container image in ECR. Due to tooling restrictions and access requirements, the build process must be executed in GitHub.com rather than in the target organization's environment. This means:

- The container image build pipeline runs in GitHub.com
- Terraform in this repo manages only build-related resources (ECR repository, build IAM roles)
- The build process cannot access internal tools or resources of the target organization
- The resulting container image is then referenced by the terraform-aws-template-automation module for actual deployment

## Overview
This document outlines the implementation plan for the Template Automation System, using an EKS cluster template as our first case study. While we'll be working with the `template-eks-cluster` repository to validate and demonstrate the system's capabilities, the core automation components (`template-automation-lambda` and `terraform-aws-template-automation`) are designed to work with any properly structured template repository.

The EKS cluster template serves as an excellent first example because it:
- Demonstrates complex configuration processing requirements
- Shows how templates can define their own workflow automation
- Provides a real-world validation of the system's flexibility
- Establishes patterns that other templates can follow

Most of the core automation work will take place in `template_automation/app.py`, while the EKS-specific template logic resides in the `template-eks-cluster` repository. This separation ensures that our automation system remains template-agnostic while allowing templates to define their own specialized behavior.

## Implementation Phases

### Phase 1: Lambda Function Core Updates
Updates to the Lambda function to establish template-agnostic repository management:

- **Branch Management**
  - Create new initialization branch instead of pushing directly to main
  - Implement flexible branch creation in GitHub client (template_automation/app.py)
  - Add robust error handling for branch operations
  - Support template-specific branch naming (e.g., "init-cluster" for EKS templates)

- **Pull Request Automation**
  - Add automatic PR creation after pushing changes
  - Implement configurable PR creation logic in GitHub client
  - Support template-specific PR templates and descriptions
  - Allow templates to define their PR strategies

### Phase 2: Template Processing Framework
Enhance the framework for processing template repositories, using EKS template as reference:

- **Configuration Processing**
  - Create flexible configuration processing system
  - Support multiple configuration formats (JSON, HCL, YAML)
  - Allow templates to define custom processing logic
  - Example: Implement config.js to HCL conversion via Ansible for EKS template

- **GitHub Actions Framework**
  - Create template-agnostic workflow framework
  - Allow templates to define custom GitHub Actions
  - Support environment-specific configurations
  - Example: Implement EKS template's generate_hcl_files.yml playbook

- **Runner Configuration**
  - Implement account-specific runner selection
  - Support lab environment runners
  - Configure runners based on AWS account IDs
  - Enable template-specific validation steps

### Phase 3: Testing Implementation
Establish comprehensive testing framework for both core system and templates:

- **Lab Environment Setup**
  - Configure workflow for lab AWS account
  - Set up isolated testing environment
  - Create test configurations for various template types
  - Example: Set up EKS cluster test configurations

- **Core System Testing**
  - Test template-agnostic functionality
  - Validate GitHub integration components
  - Test configuration processing framework
  - Verify error handling and recovery

- **End-to-End Testing**
  - Implement full workflow testing
  - Create demonstration environment
  - Add integration tests for GitHub operations
  - Test template-specific validations
  - Example: Validate EKS cluster creation workflow

### Phase 4: Documentation and Interface
Establish documentation and support infrastructure:

- **Core System Documentation**
  - Document Lambda invocation process
  - Template structure requirements
  - Configuration schema documentation
  - Template processing hooks

- **Template Development Guide**
  - Template structure guidelines
  - Best practices for template design
  - Example implementations (using EKS template)
  - Template testing guidelines

- **Future Considerations**
  - Additional template types beyond EKS
  - Enhanced template processing capabilities
  - Integration with other systems (e.g., CRF)
  - Template marketplace concept

## Success Criteria
- Core automation system successfully processes any valid template
- Templates can define their own processing logic and validation
- Comprehensive testing framework validates both system and templates
- Clear documentation helps users create new templates
- System demonstrates flexibility with multiple template types

## Dependencies
- GitHub API access and permissions
- AWS account access for testing
- Runner configurations for different environments
