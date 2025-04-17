.PHONY: install test test-unit test-integration clean

# Variables
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest
REQUIREMENTS = eks_automation/requirements.txt
TEST_DIR = eks_automation/tests
UNIT_TEST_FILE = $(TEST_DIR)/test_github_client.py
INTEGRATION_TEST_FILE = $(TEST_DIR)/test_github_client_integration.py

# Default target
all: test

# Install dependencies
install:
	$(PIP) install -r $(REQUIREMENTS)

# Run all tests
test: test-unit test-integration
	@echo "Running all tests..."
	$(PYTEST) $(TEST_DIR)

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	$(PYTEST) $(UNIT_TEST_FILE)

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	$(PYTEST) $(INTEGRATION_TEST_FILE)

# Clean up Python cache files
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
