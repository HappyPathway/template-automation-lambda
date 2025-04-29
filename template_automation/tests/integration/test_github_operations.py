import pytest
import os

@pytest.mark.integration
def test_repository_operations(test_repo, cleanup_mode):
    """Test basic repository operations."""
    # Your test code here that uses the test_repo
    
    # This is just an example verification
    assert test_repo.name.startswith("test-repo-")
    
    # Log what will happen to this repository
    if cleanup_mode:
        print(f"Repository {test_repo.name} will be DELETED after this test")
    else:
        print(f"Repository {test_repo.name} will be ARCHIVED after this test")
