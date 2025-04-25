import os
import pytest
import base64
import tempfile
import shutil
from datetime import datetime
from urllib.parse import urljoin

import requests
import requests_mock

from ..app import GitHubClient

class TestGitHubClient:
    """Test suite for GitHubClient class"""

    def test_init(self, github_client_params):
        """Test GitHubClient initialization"""
        client = GitHubClient(**github_client_params)
        assert client.api_base_url == github_client_params["api_base_url"]
        assert client.token == github_client_params["token"]
        assert client.org_name == github_client_params["org_name"]
        assert client.commit_author_name == github_client_params["commit_author_name"]
        assert client.commit_author_email == github_client_params["commit_author_email"]
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == f"token {github_client_params['token']}"

    def test_get_repository_existing(self, requests_mock, github_client_params, mock_repository_response):
        """Test getting an existing repository"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        
        # Mock the API response
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            json=mock_repository_response
        )
        
        repo = client.get_repository(repo_name)
        assert repo["name"] == mock_repository_response["name"]
        assert repo["default_branch"] == mock_repository_response["default_branch"]

    def test_get_repository_create_new(self, requests_mock, github_client_params, mock_repository_response):
        """Test creating a new repository"""
        client = GitHubClient(**github_client_params)
        repo_name = "new-test-repo"
        
        # Mock 404 for get request and success for create
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            status_code=404
        )
        requests_mock.post(
            f"{github_client_params['api_base_url']}/orgs/{github_client_params['org_name']}/repos",
            json=mock_repository_response
        )
        
        repo = client.get_repository(repo_name, create=True)
        assert repo["name"] == mock_repository_response["name"]

    def test_get_default_branch(self, requests_mock, github_client_params, mock_repository_response):
        """Test getting repository default branch"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            json=mock_repository_response
        )
        
        branch = client.get_default_branch(repo_name)
        assert branch == mock_repository_response["default_branch"]

    def test_create_blob(self, requests_mock, github_client_params, mock_blob_response):
        """Test creating a blob"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        content = b"Hello World!"
        
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/blobs",
            json=mock_blob_response
        )
        
        blob_sha = client.create_blob(repo_name, content)
        assert blob_sha == mock_blob_response["sha"]

    def test_create_tree(self, requests_mock, github_client_params, mock_tree_response):
        """Test creating a tree"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        tree_items = [{
            "path": "test.txt",
            "mode": "100644",
            "type": "blob",
            "sha": "test-blob-sha"
        }]
        
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/trees",
            json=mock_tree_response
        )
        
        tree_sha = client.create_tree(repo_name, tree_items)
        assert tree_sha == mock_tree_response["sha"]

    def test_create_commit(self, requests_mock, github_client_params, mock_commit_response):
        """Test creating a commit"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        message = "Test commit"
        tree_sha = "test-tree-sha"
        parent_shas = ["parent-sha"]
        
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/commits",
            json=mock_commit_response
        )
        
        commit_sha = client.create_commit(repo_name, message, tree_sha, parent_shas)
        assert commit_sha == mock_commit_response["sha"]

    def test_update_reference(self, requests_mock, github_client_params):
        """Test updating a reference"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        ref = "heads/main"
        sha = "test-commit-sha"
        
        requests_mock.patch(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/refs/{ref}",
            status_code=200
        )
        
        # Should not raise an exception
        client.update_reference(repo_name, ref, sha)

    def test_create_reference(self, requests_mock, github_client_params):
        """Test creating a reference"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        ref = "refs/heads/main"
        sha = "test-commit-sha"
        
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/refs",
            status_code=201
        )
        
        # Should not raise an exception
        client.create_reference(repo_name, ref, sha)

    def test_clone_repository_contents(self, requests_mock, github_client_params, mock_repository_response, 
                                    mock_reference_response, mock_tree_response, mock_blob_response, tmp_path):
        """Test cloning repository contents"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        target_dir = str(tmp_path)
        
        # Mock all required API calls
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            json=mock_repository_response
        )
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/refs/heads/main",
            json=mock_reference_response
        )
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/trees/{mock_reference_response['object']['sha']}?recursive=1",
            json=mock_tree_response
        )
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/blobs/{mock_tree_response['tree'][0]['sha']}",
            json=mock_blob_response
        )
        
        default_branch = client.clone_repository_contents(repo_name, target_dir)
        assert default_branch == mock_repository_response["default_branch"]
        assert os.path.exists(os.path.join(target_dir, mock_tree_response["tree"][0]["path"]))

    def test_commit_repository_contents(self, requests_mock, github_client_params, mock_repository_response,
                                     mock_reference_response, mock_tree_response, mock_commit_response, tmp_path):
        """Test committing repository contents"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        work_dir = str(tmp_path)
        
        # Create a test file
        test_file = os.path.join(work_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # Mock all required API calls
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            json=mock_repository_response
        )
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/refs/heads/main",
            json=mock_reference_response
        )
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/commits/{mock_reference_response['object']['sha']}",
            json=mock_commit_response
        )
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/blobs",
            json={"sha": "new-blob-sha"}
        )
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/trees",
            json={"sha": "new-tree-sha"}
        )
        requests_mock.post(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/commits",
            json={"sha": "new-commit-sha"}
        )
        requests_mock.patch(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}/git/refs/heads/main",
            status_code=200
        )
        
        default_branch = client.commit_repository_contents(repo_name, work_dir, "Test commit")
        assert default_branch == mock_repository_response["default_branch"]

    def test_error_handling(self, requests_mock, github_client_params):
        """Test error handling in GitHubClient methods"""
        client = GitHubClient(**github_client_params)
        repo_name = "test-repo"
        
        # Test error on repository creation
        requests_mock.get(
            f"{github_client_params['api_base_url']}/repos/{github_client_params['org_name']}/{repo_name}",
            status_code=404
        )
        requests_mock.post(
            f"{github_client_params['api_base_url']}/orgs/{github_client_params['org_name']}/repos",
            status_code=500,
            text="Internal Server Error"
        )
        
        with pytest.raises(Exception) as exc_info:
            client.get_repository(repo_name, create=True)
        assert "Failed to create repository" in str(exc_info.value)