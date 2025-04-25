import os
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from eks_automation.app import GitHubClient

@pytest.fixture
def mock_secrets_manager():
    with patch('boto3.session.Session') as mock_session:
        secrets_client = MagicMock()
        mock_session.return_value.client.return_value = secrets_client
        yield secrets_client

@pytest.fixture
def github_client_env():
    os.environ['GITHUB_TOKEN_SECRET_NAME'] = 'test/github-token'
    os.environ['GITHUB_ORG_NAME'] = 'test-org'
    yield
    del os.environ['GITHUB_TOKEN_SECRET_NAME']
    del os.environ['GITHUB_ORG_NAME']

def test_github_client_init_success(mock_secrets_manager, github_client_env):
    # Setup
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': 'fake-token'
    }

    # Test
    client = GitHubClient()

    # Assert
    assert client.token == 'fake-token'
    assert client.org_name == 'test-org'
    assert client.headers['Authorization'] == 'Bearer fake-token'
    mock_secrets_manager.get_secret_value.assert_called_once_with(
        SecretId='test/github-token'
    )

def test_github_client_missing_secret_name():
    # Test
    with pytest.raises(ValueError, match="GITHUB_TOKEN_SECRET_NAME environment variable is required"):
        GitHubClient()

def test_github_client_secret_not_found(mock_secrets_manager, github_client_env):
    # Setup
    mock_secrets_manager.get_secret_value.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Secret not found'}},
        'GetSecretValue'
    )

    # Test
    with pytest.raises(Exception, match="Failed to retrieve GitHub token from Secrets Manager"):
        GitHubClient()

def test_github_client_trigger_workflow_success(mock_secrets_manager, github_client_env):
    # Setup
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': 'fake-token'
    }
    
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 204
        client = GitHubClient()
        
        # Test
        result = client.trigger_workflow('test-repo')
        
        # Assert
        assert result == {"status": "success"}
        mock_post.assert_called_once()
        assert mock_post.call_args[1]['headers']['Authorization'] == 'Bearer fake-token'
