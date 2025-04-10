# EKS Automation Lambda

## Description

This repository contains source code and supporting files for a serverless application that you can deploy with the SAM CLI.
The application uses a Lambda function to process JSON input data and create a new GitHub repo for **Census EKS CI/CD pipeline**.

## Getting Started

First of all, you need access to an AWS account with adequate permission to which the resources will be deployed.
You also need to create an [`AWS CLI` profile](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html#getting-started-quickstart-new).

A [GitHub Personal Access Token (PAT)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
is required to access the Census GitHub Enterprise Server.
The `PAT` must be securely stored in `AWS Systems Manager Parameter Store`. The parameter name must match the value of the
"SECRET_NAME" constant defined in the `eks_automation/app.py` file.

To access the Census GitHub Enterprise Server, a VPC with private subnets connected to the server must also be attached.
The VPC configuration is set in the `template.yaml` file. Change the `Subnet IDs` and `Security Group IDs` as needed.

You may also want to adjust other settings (API Usage Plan, tags, etc.) in the `template.yaml` file.

## Prerequites

- git
- python3.11
- pip
- pre-commit
- AWS CLI
- SAM CLI

You may need to submit a support ticket to request the installation of these tools on your laptop.

### Installing

- Clone this repository:

  ```sh
  git clone git@github.e.it.census.gov:SCT-Engineering/eks-automation-lambda.git
  ```

- After cloning, access the folder and install `pre-commit hooks` listed in the `.pre-commit-config.yaml`:

  ```sh
  cd eks-automation-lambda
  pre-commit install
  ```

## Deploy/Test the application

- Create an `AWS S3 bucket`:

  ```sh
  aws s3api create-bucket --bucket eks-automation-lambda-s3-bucket \
  --create-bucket-configuration LocationConstraint=us-gov-east-1 \
  --region us-gov-east-1 \
  --profile 229685449397-csvd-dev-gov
  ```

  The `bucket name` must match the one specified in the `samconfig.toml` file.
  Please adjust the profile name and region accordingly.

- Download [`git-lambda-layer`](https://github.com/lambci/git-lambda-layer/blob/master/lambda2/layer.zip) `zip` file.
- Upload `git-lambda-layer` to the newly created `AWS S3 bucket`:

  ```sh
  aws s3 cp {download-folder}/layer.zip s3://eks-automation-lambda-s3-bucket/ --profile 229685449397-csvd-dev-gov
  ```

- Build the application:

  ```sh
  sam build
  ```

- Deploy the application:

  ```sh
  sam deploy --profile 229685449397-csvd-dev-gov
  ```

  Save the `API Gateway endpoint URL` listed in the output. You will need this URL for testing.

- Test:

  The input `JSON` payload is in the following format:

  ```json
  {
    "project_name": "string",
    "eks_settings": {
      "attrs": {
        "attribute1": "value1",
        "attribute2": "value2",
        ...
      },
      "tags" : {
        "key1": "value1",
        "key2": "value2",
        ...
      }
    }
  }
  ```

  Get the `API Key`:

  ```sh
  aws apigateway get-api-keys --query 'items[?contains(name, `eks-`)].value' --include-values --output text --profile 229685449397-csvd-dev-gov
  ```

  ```sh
  curl -X POST -H "X-API-Key: {API Key}"  https://{API Gateway endpoint URL} -d '
  {
    "project_name": "eks-automation-lambda-test",
    "eks_settings": {
      "attrs": {
        "account_name": "lab-dev-ew",
        "aws_region": "us-gov-east-1",
        "cluster_mailing_list": "someone@census.gov",
        "cluster_name": "csvd-platform-lab-mcm",
        "eks_instance_disk_size": 100,
        "eks_ng_desired_size": 2,
        "eks_ng_max_size": 10,
        "eks_ng_min_size": 2,
        "environment": "development",
        "environment_abbr": "dev",
        "organization": "census:ocio:csvd",
        "finops_project_name": "csvd_platformbaseline",
        "finops_project_number": "fs0000000078",
        "finops_project_role": "csvd_platformbaseline_app",
        "vpc_domain_name": "dev.lab.csp2.census.gov",
        "vpc_name": "vpc3-lab-dev"
      },
      "tags" : {
        "slim:schedule": "8:00-17:00"
      }
    }
  }
  '
  ```

  Replace `{API Key}` with the result of the last command and `{API Gateway endpoint URL}` with the value saved from the `sam deploy` command output.

## Resources

- [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Git Lambda Layer](https://github.com/lambci/git-lambda-layer/)
- [AWS API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [PyGithub](https://pygithub.readthedocs.io/en/stable/introduction.html)
- [GitPython](https://gitpython.readthedocs.io/en/stable/)
