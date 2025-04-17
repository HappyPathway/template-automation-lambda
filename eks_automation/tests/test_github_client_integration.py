import os
import json
import pytest
import requests
import tempfile
import shutil
import uuid
import time
from datetime import datetime

from ..app import GitHubClient

# Skip all tests if no GitHub token is available
pytestmark = [
    pytest.mark.skipif(
        "GITHUB_TOKEN" not in os.environ,
        reason="GITHUB_TOKEN environment variable not set"
    ),
    pytest.mark.integration
]

@pytest.fixture
def integration_client():
    """Create a GitHubClient instance for integration testing"""
    token = os.environ["GITHUB_TOKEN"]
    api_url = os.environ.get("GITHUB_API", "https://api.github.com")
    org_name = os.environ.get("GITHUB_ORG", "test-org")
    
    client = GitHubClient(
        api_base_url=api_url,
        token=token,
        org_name=org_name,
        commit_author_name="Integration Test",
        commit_author_email="test@example.com",
        source_version=None,
        template_repo_name="template-lambda-deployment",
        config_file_name="config.json"
    )
    return client

@pytest.fixture
def temp_repo_name():
    """Generate a unique temporary repository name"""
    return f"temp-test-repo-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def cleanup_repo(integration_client):
    """Fixture to clean up test repository after tests"""
    repo_names = []
    
    def _register_repo(repo_name):
        repo_names.append(repo_name)
        return repo_name
    
    yield _register_repo
    
    # Clean up all registered repos
    for repo_name in repo_names:
        try:
            # Note: Real deletion would require additional API calls
            # For safety in testing, we just archive the repo
            requests.patch(
                f"{integration_client.api_base_url}/repos/{integration_client.org_name}/{repo_name}",
                headers=integration_client.headers,
                json={"archived": True},
                verify=False
            )
        except Exception as e:
            print(f"Failed to archive repository {repo_name}: {e}")

class TestGitHubClientIntegration:
    """Integration tests for GitHubClient using real GitHub API"""
    
    def test_repository_creation(self, integration_client, temp_repo_name, cleanup_repo):
        """Test creating a new repository via the API"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = integration_client.get_repository(repo_name, create=True)
        
        assert repo is not None
        assert repo["name"] == repo_name
        assert not repo["archived"]
        
        # Verify we can get the repository
        repo = integration_client.get_repository(repo_name)
        assert repo["name"] == repo_name
    
    def test_file_operations(self, integration_client, temp_repo_name, cleanup_repo, tmp_path):
        """Test file operations with real repository"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = integration_client.get_repository(repo_name, create=True)
        
        # Create a test file
        test_content = {
            "test": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Write test content to work directory
        work_dir = str(tmp_path)
        os.makedirs(work_dir, exist_ok=True)
        test_file = os.path.join(work_dir, "test-config.json")
        
        with open(test_file, "w") as f:
            json.dump(test_content, f, indent=2)
        
        # Commit the file
        integration_client.commit_repository_contents(
            repo_name,
            work_dir,
            "Test commit from integration tests"
        )
        
        # Add a short delay to allow GitHub API to become consistent
        time.sleep(2)
        
        # Verify the file exists in the repository
        # Clone to a new directory and verify contents
        clone_dir = os.path.join(str(tmp_path), "clone")
        os.makedirs(clone_dir, exist_ok=True)
        
        integration_client.clone_repository_contents(repo_name, clone_dir)
        
        cloned_file = os.path.join(clone_dir, "test-config.json")
        assert os.path.exists(cloned_file)
        
        with open(cloned_file, "r") as f:
            cloned_content = json.load(f)
        
        assert cloned_content["test"] == test_content["test"]
        assert cloned_content["timestamp"] == test_content["timestamp"]
    
    def test_branch_operations(self, integration_client, temp_repo_name, cleanup_repo, tmp_path):
        """Test branch creation and updates"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = integration_client.get_repository(repo_name, create=True)
        
        # Create a test file and commit to main
        work_dir = str(tmp_path)
        os.makedirs(work_dir, exist_ok=True)
        
        with open(os.path.join(work_dir, "test.txt"), "w") as f:
            f.write("main branch content")
        
        # Commit to main
        integration_client.commit_repository_contents(
            repo_name,
            work_dir,
            "Initial commit",
            branch="main"
        )
        
        # Create a new branch
        main_sha = integration_client.get_reference_sha(repo_name, "heads/main")
        integration_client.create_reference(
            repo_name,
            "refs/heads/test-branch",
            main_sha
        )
        
        # Update file in new branch
        with open(os.path.join(work_dir, "test.txt"), "w") as f:
            f.write("test branch content")
        
        # Commit to test branch
        integration_client.commit_repository_contents(
            repo_name,
            work_dir,
            "Update in test branch",
            branch="test-branch"
        )
        
        # Verify the changes
        clone_dir = os.path.join(str(tmp_path), "clone")
        os.makedirs(clone_dir, exist_ok=True)
        
        # Clone and verify main branch
        main_dir = os.path.join(clone_dir, "main")
        integration_client.clone_repository_contents(repo_name, main_dir, branch="main")
        
        with open(os.path.join(main_dir, "test.txt"), "r") as f:
            main_content = f.read()
        assert main_content == "main branch content"
        
        # Clone and verify test branch contents
        test_dir = os.path.join(clone_dir, "test")
        integration_client.clone_repository_contents(repo_name, test_dir, branch="test-branch")
        
        with open(os.path.join(test_dir, "test.txt"), "r") as f:
            test_content = f.read()
        assert test_content == "test branch content"