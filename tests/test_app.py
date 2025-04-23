import os
import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from eks_automation.app import get_parameter, operate_github

@pytest.fixture
def mock_ssm():
    with patch('boto3.client') as mock_client:
        ssm_client = MagicMock()
        mock_client.return_value = ssm_client
        yield ssm_client

@pytest.fixture
def mock_secrets():
    with patch('eks_automation.app.github_token') as mock_token:
        mock_token.return_value = 'fake-token'
        yield mock_token

def test_get_parameter_from_ssm(mock_ssm):
    # Setup
    mock_ssm.get_parameter.return_value = {
        'Parameter': {'Value': 'param-value'}
    }

    # Test
    result = get_parameter('test-param')

    # Assert
    assert result == 'param-value'
    mock_ssm.get_parameter.assert_called_once_with(
        Name='/template-automation/test-param',
        WithDecryption=False
    )

def test_get_parameter_from_env(mock_ssm):
    # Setup
    mock_ssm.get_parameter.side_effect = ClientError(
        {'Error': {'Code': 'ParameterNotFound'}},
        'GetParameter'
    )
    os.environ['test-param'] = 'env-value'

    # Test
    result = get_parameter('test-param')

    # Assert
    assert result == 'env-value'

def test_get_parameter_with_default(mock_ssm):
    # Setup
    mock_ssm.get_parameter.side_effect = ClientError(
        {'Error': {'Code': 'ParameterNotFound'}},
        'GetParameter'
    )

    # Test
    result = get_parameter('missing-param', default='default-value')

    # Assert
    assert result == 'default-value'

@patch('eks_automation.app.GitHubClient')
def test_operate_github_success(mock_github_client, mock_secrets):
    # Setup
    mock_client = MagicMock()
    mock_github_client.return_value = mock_client
    
    # Set required environment variables
    os.environ['GITHUB_API'] = 'https://api.github.com'
    os.environ['GITHUB_ORG_NAME'] = 'test-org'
    os.environ['TEMPLATE_REPO_NAME'] = 'template-repo'

    # Test data
    new_repo_name = 'test-repo'
    template_settings = {'key': 'value'}

    # Test
    operate_github(new_repo_name, template_settings)

    # Assert
    mock_client.get_repository.assert_called()
    mock_client.commit_repository_contents.assert_called()
    mock_client.update_repository_topics.assert_called()

@pytest.mark.parametrize('missing_param', ['GITHUB_API', 'GITHUB_ORG_NAME', 'TEMPLATE_REPO_NAME'])
def test_operate_github_missing_required_params(missing_param, mock_secrets):
    # Setup
    required_params = {
        'GITHUB_API': 'https://api.github.com',
        'GITHUB_ORG_NAME': 'test-org',
        'TEMPLATE_REPO_NAME': 'template-repo'
    }
    
    # Remove one required parameter
    test_params = required_params.copy()
    del test_params[missing_param]
    
    # Set environment variables
    for key, value in test_params.items():
        os.environ[key] = value
    if missing_param in os.environ:
        del os.environ[missing_param]

    # Test
    with pytest.raises(ValueError) as exc_info:
        operate_github('test-repo', {'key': 'value'})
    
    assert missing_param in str(exc_info.value)
