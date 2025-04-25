import os
import json
import pytest
import requests
import tempfile
import shutil
import uuid
import time
import logging
from datetime import datetime

from ..app import GitHubClient

# Skip all tests if no GitHub token is available
pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("GITHUB_TOKEN") or 
        not os.environ.get("GITHUB_API") or 
        not os.environ.get("GITHUB_ORG"),
        reason="Missing required GitHub environment variables"
    ),
    pytest.mark.integration
]

class TestGitHubClientIntegration:
    """Integration tests for GitHubClient class"""
    
    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup GitHubClient instance for tests"""
        self.client = GitHubClient(
            os.environ["GITHUB_API"],
            os.environ["GITHUB_TOKEN"],
            os.environ["GITHUB_ORG"],
            "Integration Test",
            "test@example.com"
        )

    @pytest.fixture
    def cleanup_repo(self):
        """Fixture to track and cleanup test repositories"""
        created_repos = []

        def _register_repo(repo_name):
            created_repos.append(repo_name)
            return repo_name

        yield _register_repo

        # Cleanup: Archive all created test repositories
        for repo in created_repos:
            try:
                archive_url = f"{os.environ['GITHUB_API']}/repos/{os.environ['GITHUB_ORG']}/{repo}"
                response = requests.patch(
                    archive_url,
                    headers={
                        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json={"archived": True},
                    verify=False
                )
                if response.status_code != 200:
                    logging.warning(f"Failed to archive repository {repo}: {response.status_code}")
            except Exception as e:
                logging.warning(f"Error archiving repository {repo}: {str(e)}")

    @pytest.fixture
    def temp_repo_name(self):
        """Generate a unique temporary repository name"""
        return f"temp-test-repo-{uuid.uuid4().hex[:8]}"

    def test_repository_creation(self, temp_repo_name, cleanup_repo):
        """Test repository creation"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = self.client.get_repository(repo_name, create=True)
        
        assert repo["name"] == repo_name
        assert not repo["archived"]
        assert repo["private"]

    def test_file_operations(self, temp_repo_name, cleanup_repo):
        """Test file operations"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = self.client.get_repository(repo_name, create=True)
        
        # Create a test file
        test_content = {
            "test": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Create temporary directory
        with tempfile.TemporaryDirectory() as work_dir:
            test_file = os.path.join(work_dir, "test-config.json")
            
            # Write test content
            with open(test_file, "w") as f:
                json.dump(test_content, f, indent=2)
            
            # Commit the file
            branch = self.client.commit_repository_contents(
                repo_name,
                work_dir,
                "Test commit from integration tests"
            )
            assert branch == "main"
            
            # Add a small delay to ensure GitHub API has processed the commit
            time.sleep(2)
            
            # Verify we can clone the repository with the file
            output_dir = os.path.join(work_dir, "clone")
            cloned_branch = self.client.clone_repository_contents(repo_name, output_dir)
            
            assert cloned_branch == "main"
            assert os.path.exists(os.path.join(output_dir, "test-config.json"))

    def test_branch_operations(self, temp_repo_name, cleanup_repo):
        """Test branch operations"""
        repo_name = cleanup_repo(temp_repo_name)
        
        # Create new repository
        repo = self.client.get_repository(repo_name, create=True)
        
        # Create a test file in main branch
        with tempfile.TemporaryDirectory() as work_dir:
            # Initial commit on main branch
            main_file = os.path.join(work_dir, "test.txt")
            with open(main_file, "w") as f:
                f.write("main branch content")
            
            self.client.commit_repository_contents(
                repo_name,
                work_dir,
                "Initial commit on main"
            )
            
            # Create and switch to a test branch
            test_branch = "test-branch"
            # Clean directory for test branch changes
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            
            # Create different content in test branch
            with open(main_file, "w") as f:
                f.write("test branch content")
            
            self.client.commit_repository_contents(
                repo_name,
                work_dir,
                "Commit on test branch",
                branch=test_branch
            )
            
            # Clone and verify main branch content
            main_output = os.path.join(work_dir, "clone-main")
            os.makedirs(main_output, exist_ok=True)
            self.client.clone_repository_contents(repo_name, main_output, branch="main")
            
            with open(os.path.join(main_output, "test.txt")) as f:
                assert f.read().strip() == "main branch content"
            
            # Clone and verify test branch content
            test_output = os.path.join(work_dir, "clone-test")
            os.makedirs(test_output, exist_ok=True)
            self.client.clone_repository_contents(repo_name, test_output, branch=test_branch)
            
            with open(os.path.join(test_output, "test.txt")) as f:
                assert f.read().strip() == "test branch content"
