import os
import pytest
from template_automation.github_client import GitHubClient
from github import GithubException

# Configuration from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_ORG = os.getenv("GITHUB_ORG", "test-organization")
TEST_REPO_PREFIX = "test-automation-"

def is_integration_test_enabled():
    """Check if integration tests should run based on environment variables."""
    return bool(GITHUB_TOKEN and GITHUB_ORG)

@pytest.fixture(scope="session")
def github_client():
    """Create a GitHub client for testing."""
    if not is_integration_test_enabled():
        pytest.skip("Integration tests disabled - missing required environment variables")
    
    return GitHubClient(
        api_base_url=GITHUB_API_URL,
        token=GITHUB_TOKEN,
        org_name=GITHUB_ORG
    )

@pytest.fixture(autouse=True)
def cleanup_test_repos(github_client):
    """Cleanup test repositories before and after tests."""
    if not is_integration_test_enabled():
        return
        
    # Cleanup before test
    try:
        repos = github_client.org.get_repos()
        for repo in repos:
            if repo.name.startswith(TEST_REPO_PREFIX):
                repo.delete()
    except GithubException as e:
        print(f"Cleanup warning: {e}")
    
    yield
    
    # Cleanup after test
    try:
        repos = github_client.org.get_repos()
        for repo in repos:
            if repo.name.startswith(TEST_REPO_PREFIX):
                repo.delete()
    except GithubException as e:
        print(f"Cleanup warning: {e}")

@pytest.mark.integration
def test_repository_creation(github_client):
    """Test basic repository creation and deletion."""
    repo_name = f"{TEST_REPO_PREFIX}basic"
    
    # Test repository creation
    repo = github_client.get_repository(repo_name, create=True)
    assert repo.name == repo_name
    assert repo.private is True
    
    # Verify repository exists
    repo = github_client.get_repository(repo_name)
    assert repo.name == repo_name

@pytest.mark.integration
def test_branch_operations(github_client):
    """Test branch creation and management."""
    repo_name = f"{TEST_REPO_PREFIX}branches"
    branch_name = "test-branch"
    
    # Create repository and branch
    repo = github_client.get_repository(repo_name, create=True)
    github_client.create_branch(repo_name, branch_name)
    
    # Verify branch exists
    repo = github_client.get_repository(repo_name)
    branch = repo.get_branch(branch_name)
    assert branch.name == branch_name

@pytest.mark.integration
def test_file_operations(github_client):
    """Test file creation, reading, and updating."""
    repo_name = f"{TEST_REPO_PREFIX}files"
    test_file = "test.txt"
    initial_content = "Hello, World!"
    updated_content = "Updated content"
    
    # Create repository and file
    repo = github_client.get_repository(repo_name, create=True)
    github_client.write_file(repo, test_file, initial_content)
    
    # Read and verify content
    content = github_client.read_file(repo, test_file)
    assert content == initial_content
    
    # Update and verify
    github_client.write_file(repo, test_file, updated_content)
    content = github_client.read_file(repo, test_file)
    assert content == updated_content

@pytest.mark.integration
def test_pull_request_workflow(github_client):
    """Test pull request creation workflow."""
    repo_name = f"{TEST_REPO_PREFIX}pr"
    branch_name = "feature-branch"
    
    # Setup repository and branch
    repo = github_client.get_repository(repo_name, create=True)
    github_client.create_branch(repo_name, branch_name)
    
    # Create PR
    pr = github_client.create_pull_request(
        repo_name=repo_name,
        title="Test PR",
        body="Testing pull request creation",
        head_branch=branch_name
    )
    
    assert pr.title == "Test PR"
    assert pr.head.ref == branch_name
    assert pr.base.ref == "main"

@pytest.mark.integration
def test_team_permissions(github_client):
    """Test team permission management."""
    repo_name = f"{TEST_REPO_PREFIX}team-perms"
    team_name = os.getenv("GITHUB_TEST_TEAM")
    
    if not team_name:
        pytest.skip("Skipping team permission test - GITHUB_TEST_TEAM not set")
    
    # Create repository
    repo = github_client.get_repository(repo_name, create=True)
    
    # Set and verify team permissions
    github_client.set_team_permission(repo_name, team_name, "admin")
    
    # Verify team has access (this will raise an exception if access is not granted)
    team = github_client.org.get_team_by_slug(team_name)
    assert team.has_in_repos(repo)
