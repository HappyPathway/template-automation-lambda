import os
import json
import pytest
import uuid
from eks_automation.app import lambda_handler

# Test environment variables
os.environ["SECRET_NAME"] = "github-token"  # Uses AWS Secrets Manager
os.environ["GITHUB_API"] = "https://api.github.com"
os.environ["GITHUB_ORG_NAME"] = "your-org-name"  # Replace with test org
os.environ["TEMPLATE_REPO_NAME"] = "template-eks-cluster"
os.environ["TEMPLATE_SOURCE_VERSION"] = "main"  # Or specific tag/SHA for testing

@pytest.fixture
def test_event():
    """Create test event with unique repository name"""
    repo_name = f"test-eks-cluster-{uuid.uuid4().hex[:8]}"
    return {
        "body": {
            "project_name": repo_name,
            "eks_settings": {
                "cluster_name": "test-cluster",
                "kubernetes_version": "1.27",
                "region": "us-west-2",
                "vpc_config": {
                    "vpc_id": "vpc-test123",
                    "subnet_ids": ["subnet-test1", "subnet-test2"]
                },
                "nodegroups": [{
                    "name": "test-ng",
                    "instance_types": ["t3.medium"],
                    "desired_size": 2,
                    "min_size": 1,
                    "max_size": 3
                }]
            }
        }
    }

@pytest.fixture
def lambda_context():
    """Mock Lambda context object"""
    class MockContext:
        def __init__(self):
            self.aws_request_id = "test-request-id"
        def get_remaining_time_in_millis(self):
            return 30000
    return MockContext()

def test_lambda_handler_creates_repository(test_event, lambda_context):
    """Test that Lambda handler creates repository with correct settings"""
    # Execute Lambda handler
    response = lambda_handler(test_event, lambda_context)
    
    assert response["statusCode"] == 200
    assert "Success" in response["body"]
    
    # Additional assertions could verify:
    # - Repository was created in GitHub
    # - Config file contains correct settings
    # - Topics were set correctly
    # But these require GitHub API access
