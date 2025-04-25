import os
import pytest

@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test"""
    # Save original environment
    env_orig = dict(os.environ)
    
    # Run test
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(env_orig)
