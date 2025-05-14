"""AWS Lambda function for creating GitHub repositories from templates.

This module provides a Lambda function handler that automates the creation of new GitHub repositories
from a template repository. It validates input, writes configuration files, and creates pull requests
to set up the new repository.

Features:
    - Template agnostic: Works with any type of template repository
    - Team-based access control: Automated team permission setup
    - Configuration management: Writes template configuration via pull request
    - Workflow automation: Optional initialization workflow trigger
    - Pure Python implementation: No Git CLI dependency
    - AWS integration: Uses Secrets Manager for token storage

Configuration:
    The Lambda function is configured through environment variables:

    Required:
        GITHUB_API: Base URL for GitHub API server
        GITHUB_ORG_NAME: Name of GitHub organization to manage
        TEMPLATE_REPO_NAME: Name of the template repository to use
        GITHUB_TOKEN_SECRET_NAME: Name of AWS Secrets Manager secret containing GitHub token

    Optional:
        TEMPLATE_CONFIG_FILE: Name of config file to write (default: config.json)
        TEMPLATE_TOPICS: Comma-separated topics to add (default: infrastructure)
        PARAM_STORE_PREFIX: Prefix for SSM parameters (default: /template-automation)
        GITHUB_COMMIT_AUTHOR_NAME: Name for commits (default: Template Automation)
        GITHUB_COMMIT_AUTHOR_EMAIL: Email for commits (default: automation@example.com)
        TEMPLATE_SOURCE_VERSION: Version/tag/SHA to use from template

See Also:
    - GitHubClient: Handles all GitHub API interactions
    - TemplateManager: Manages template configuration and rendering
    - models.TemplateInput: Validates Lambda function input
"""

import os
import logging
import time
import traceback
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from .models import TemplateInput, GitHubConfig
from .template_manager import TemplateManager
from .github_client import GitHubClient

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")  # Set to "ERROR" to reduce logging messages.

# Required environment variables
REQUIRED_ENV_VARS = [
    "GITHUB_API",
    "GITHUB_ORG_NAME",
    "TEMPLATE_REPO_NAME",
    "GITHUB_TOKEN_SECRET_NAME"
]

# Check if we're being imported for documentation
IN_SPHINX_BUILD = os.environ.get('SPHINX_BUILD') == '1'

# Skip validation during documentation build
if not IN_SPHINX_BUILD:
    # Validate required environment variables
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Get environment variables with defaults for documentation
GITHUB_TOKEN_SECRET_NAME = os.environ.get("GITHUB_TOKEN_SECRET_NAME", "docs-placeholder")
DEFAULT_CONFIG_FILE = os.environ.get("TEMPLATE_CONFIG_FILE", "config.json")
DEFAULT_TOPICS = os.environ.get("TEMPLATE_TOPICS", "infrastructure").split(",")
PARAM_STORE_PREFIX = os.environ.get("PARAM_STORE_PREFIX", "/template-automation")
TEMPLATE_SOURCE_VERSION: Optional[str] = os.environ.get("TEMPLATE_SOURCE_VERSION")
# Add SSL verification environment variable with default to True (secure)
VERIFY_SSL = os.environ.get("VERIFY_SSL", "true").lower() != "false"

# Keep imports and logging setup from here
# The GitHubClient class has been moved to github_client.py

def lambda_handler(event: dict, context) -> dict:
    """Process requests to create new repositories from templates.

    The handler executes the following steps:
    1. Validates the input event using TemplateInput model
    2. Retrieves GitHub token from AWS Secrets Manager
    3. Initializes GitHub client and template manager
    4. Creates new repository with team permissions
    5. Creates a feature branch for configuration
    6. Writes template configuration file
    7. Creates a pull request with the changes
    8. Optionally triggers initialization workflow

    Args:
        event: AWS Lambda event containing:
            project_name (str): Name for the new repository
            template_settings (dict): Configuration values for the template
            trigger_init_workflow (bool): Whether to trigger initialization
            owning_team (str, optional): GitHub team to grant admin access
        context: AWS Lambda context object (unused)

    Returns:
        dict: Creation results containing:
            repository_url (str): URL of the created repository
            pull_request_url (str, optional): URL of the config pull request

    Raises:
        ValueError: If input validation fails
        ClientError: On AWS Secrets Manager errors
        GithubException: On GitHub API errors.

    Example:
        >>> event = {
        ...     "project_name": "my-new-service",
        ...     "template_settings": {
        ...         "environment": "production",
        ...         "region": "us-west-2"
        ...     },
        ...     "trigger_init_workflow": True,
        ...     "owning_team": "platform-team"
        ... }
        >>> result = lambda_handler(event, None)
        >>> print(result["repository_url"])
         'https://github.com/myorg/my-new-service'
    """
    try:
        logger.info(f"Processing template request: {event}")

        # Parse and validate input
        template_input = TemplateInput(**event)
        logger.info(f"Validated input for project: {template_input.project_name}")

        # Get GitHub configuration from environment/parameter store
        github_config = GitHubConfig(
            api_base_url=get_github_base_url(os.environ["GITHUB_API"]),
            org_name=os.environ["GITHUB_ORG_NAME"],
            commit_author_name=os.environ.get("GITHUB_COMMIT_AUTHOR_NAME", "Template Automation"),
            commit_author_email=os.environ.get("GITHUB_COMMIT_AUTHOR_EMAIL", "automation@example.com"),
            token=get_github_token(),
            template_repo_name=os.environ["TEMPLATE_REPO_NAME"],
            config_file_name=DEFAULT_CONFIG_FILE,
            source_version=TEMPLATE_SOURCE_VERSION,
        )

        # Initialize clients
        github = GitHubClient(
            api_base_url=github_config.api_base_url,
            token=github_config.token,
            org_name=github_config.org_name,
            commit_author_name=github_config.commit_author_name,
            commit_author_email=github_config.commit_author_email,
            verify_ssl=VERIFY_SSL  # Pass SSL verification setting
        )
        
        # Initialize TemplateManager with proper parameters
        template_mgr = TemplateManager(template_repo_name=github_config.template_repo_name)

        # Create repository from template
        repo_name = template_input.project_name
        repo = github.get_repository(repo_name, create=True, owning_team=template_input.owning_team)

        # Create feature branch for template configuration
        feature_branch = f"template-config-{int(time.time())}"
        github.create_branch(repo_name, feature_branch)

        # Write template configuration
        github.write_file(
            repo=repo,
            path=DEFAULT_CONFIG_FILE,
            content=template_input.template_settings.json(),
            branch=feature_branch,
            commit_message=f"Initialize {DEFAULT_CONFIG_FILE} from template"
        )

        # Set repository topics
        github.update_repository_topics(repo_name, DEFAULT_TOPICS)

        # Create pull request with template configuration
        pr_details = template_mgr.render_pr_details(
            repo_name=repo_name,
            workflow_files=[DEFAULT_CONFIG_FILE]
        )
        
        pr = github.create_pull_request(
            repo_name=repo_name,
            title=pr_details["title"],
            body=pr_details["body"],
            head_branch=feature_branch,
            base_branch=github.get_default_branch(repo_name)
        )

        # Optionally trigger initialization workflow
        if template_input.trigger_init_workflow:
            github.trigger_workflow(
                repo_name=repo_name,
                workflow_id="initialize.yml",
                ref=feature_branch
            )

        return {
            "repository_url": repo.html_url,
            "pull_request_url": pr.html_url if pr else None
        }
    except Exception as e:
        logger.error(f"Failed to process template request: {str(e)}")
        logger.debug(traceback.format_exc())
        raise


def get_github_token() -> str:
    """Get GitHub token from AWS Secrets Manager.
    
    Returns:
        str: GitHub API token
        
    Raises:
        ClientError: If secret retrieval fails
    """
    try:
        # Configure boto3 to skip SSL verification if needed
        session = boto3.session.Session()
        client_kwargs = {}
        
        if not VERIFY_SSL:
            client_kwargs['verify'] = False
            # Suppress boto3 warning messages about insecure connections
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        client = session.client('secretsmanager', **client_kwargs)
        response = client.get_secret_value(SecretId=GITHUB_TOKEN_SECRET_NAME)
        return response['SecretString']
    except ClientError as e:
        logger.error(f"Failed to get GitHub token: {str(e)}")
        raise


def get_github_base_url(api_url: str) -> str:
    """Normalize GitHub API URL for GitHub Enterprise Server.
    
    Args:
        api_url: Raw GitHub API URL from environment
    
    Returns:
        Normalized base URL for GitHub API
    """
    # Remove trailing slashes and /api/v3 if present
    base_url = api_url.rstrip('/')
    if base_url.endswith('/api/v3'):
        base_url = base_url[:-7]
    elif '/api/v3' in base_url:
        # In some GitHub Enterprise setups, the URL might be like https://github.e.it.census.gov/api/v3
        # Extract just the server part
        base_url = base_url.split('/api/v3')[0]
    
    logger.info(f"Using GitHub base URL: {base_url}")
    return base_url
