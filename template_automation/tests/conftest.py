import os
import pytest
from github import Github
import time

@pytest.fixture(scope="session")
def github_client():
    """Create a GitHub client for integration tests."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN environment variable not set")
    
    api_url = os.environ.get("GITHUB_API", "https://api.github.com")
    return Github(base_url=api_url, login_or_token=token)

@pytest.fixture(scope="session")
def cleanup_mode():
    """Determine if repositories should be deleted or just archived."""
    return os.environ.get("INTEGRATION_TEST_DELETE_REPOS", "").lower() in ("true", "1", "yes")

@pytest.fixture
def test_repo(github_client, cleanup_mode, request):
    """Create a test repository and clean it up after the test."""
    org_name = os.environ.get("GITHUB_ORG")
    if not org_name:
        pytest.skip("GITHUB_ORG environment variable not set")
    
    # Create a unique repo name for this test
    repo_name = f"test-repo-{pytest.config.getoption('--timestamp', default='')}-{id(request)}"
    
    org = github_client.get_organization(org_name)
    repo = org.create_repo(
        repo_name,
        description="Temporary repository for integration testing",
        private=True
    )
    
    yield repo
    
    # Clean up after the test
    if cleanup_mode:
        # Delete the repository
        repo.delete()
    else:
        # Archive the repository (the original behavior)
        repo.edit(archived=True)

@pytest.fixture
def github_client_params():
    """Fixture providing standard GitHubClient parameters"""
    return {
        "api_base_url": "https://api.github.example.com",
        "token": "test-token",
        "org_name": "test-org",
        "commit_author_name": "Test Author",
        "commit_author_email": "test@example.com",
        "source_version": "v1.0.0",
        "template_repo_name": "template-repo",
        "config_file_name": "config.json"
    }

@pytest.fixture
def mock_repository_response():
    """Fixture providing a standard repository API response"""
    return {
        "id": 1234,
        "name": "test-repo",
        "default_branch": "main",
        "private": True,
        "description": "Test repository"
    }

@pytest.fixture
def mock_tree_response():
    """Fixture providing a standard tree API response"""
    return {
        "sha": "test-tree-sha",
        "tree": [
            {
                "path": "test.txt",
                "mode": "100644",
                "type": "blob",
                "sha": "test-blob-sha",
                "size": 100
            }
        ]
    }

@pytest.fixture
def mock_blob_response():
    """Fixture providing a standard blob API response"""
    return {
        "sha": "test-blob-sha",
        "content": "SGVsbG8gV29ybGQh",  # Base64 encoded "Hello World!"
        "encoding": "base64"
    }

@pytest.fixture
def mock_commit_response():
    """Fixture providing a standard commit API response"""
    return {
        "sha": "test-commit-sha",
        "tree": {
            "sha": "test-tree-sha"
        }
    }

@pytest.fixture
def mock_reference_response():
    """Fixture providing a standard reference API response"""
    return {
        "ref": "refs/heads/main",
        "object": {
            "sha": "test-commit-sha",
            "type": "commit"
        }
    }

def pytest_addoption(parser):
    """Add custom command line options."""
    timestamp = int(time.time())
    parser.addoption("--timestamp", action="store", default=str(timestamp))