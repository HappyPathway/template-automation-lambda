import pytest
import os
import json

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