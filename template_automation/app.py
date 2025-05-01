####################################################################################
# This Lambda function creates new GitHub repositories from a template repository.
# It takes JSON input and writes it to a configurable config file in the new repo.
# Key features:
# - Template agnostic: Can be used with any type of template repository
# - Team-based admin access: Set owning team with full admin access
# - Configurable settings via Parameter Store (with prefix) or environment variables:
#   - PARAM_STORE_PREFIX: Prefix for SSM parameters (default: /template-automation)
#   - TEMPLATE_CONFIG_FILE: Name of config file to write (default: config.json)
#   - TEMPLATE_TOPICS: Comma-separated list of topics to add (default: infrastructure)
#   - TEMPLATE_REPO_NAME: Source template repository name (required)
#   - TEMPLATE_SOURCE_VERSION: Version/tag/SHA to use from template (optional)
#   - REPO_NAME_PREFIX: Prefix for generated repository names (optional)
#   - GITHUB_API: GitHub API URL (required)
#   - GITHUB_ORG_NAME: GitHub organization name (required)
#   - GITHUB_COMMIT_AUTHOR_NAME: Name for commits (default: Template Automation)
#   - GITHUB_COMMIT_AUTHOR_EMAIL: Email for commits (default: automation@example.com)
#   - SECRET_NAME: AWS Secrets Manager secret containing GitHub token (required)
#
# Repository naming:
# - If REPO_NAME_PREFIX is set: Creates repos named {prefix}-{random-8-chars}
# - If not set: Uses the provided project name directly
#
# Implementation uses pure Python with requests library (no Git CLI dependency).
####################################################################################

import os
import stat
import shutil
import logging
import base64
import time
from datetime import datetime
import traceback
import uuid
from github import Github, GithubException
from github.GithubObject import NotSet
from github.InputGitTreeElement import InputGitTreeElement
from botocore.exceptions import ClientError
from .models import TemplateInput, GitHubConfig, WorkflowConfig
from .template_manager import TemplateManager

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")  # Set to "ERROR" to reduce logging messages.

# Get environment variables
GITHUB_TOKEN_SECRET_NAME = os.environ.get("GITHUB_TOKEN_SECRET_NAME")
DEFAULT_CONFIG_FILE = os.environ.get("TEMPLATE_CONFIG_FILE", "config.json")
DEFAULT_TOPICS = os.environ.get("TEMPLATE_TOPICS", "infrastructure").split(",")
PARAM_STORE_PREFIX = os.environ.get("PARAM_STORE_PREFIX", "/template-automation")

class GitHubClient:
    """An object-oriented interface for GitHub repository management and automation.

    This class provides a high-level interface to GitHub's API using PyGithub,
    enabling repository creation, content management, branch operations, and more.
    It's specifically designed for template-based repository automation.

    Attributes:
        github (Github): The PyGithub client instance.
        org (Organization): The GitHub organization being operated on.
        commit_author_name (str): The name to use for commit authorship.
        commit_author_email (str): The email to use for commit authorship.
        source_version (str, optional): The version, tag, or SHA of the template.
        template_repo_name (str, optional): The name of the template repository.
        config_file_name (str): The name of the configuration file to write.
    """

    def __init__(self, config: GitHubConfig):
        """Initialize the GitHub client with configuration.

        Args:
            config (GitHubConfig): A Pydantic model containing validated GitHub configuration.
                This includes the base URL, token, organization name, and other settings.
        """
        self.github = Github(
            base_url=config.api_base_url,
            login_or_token=config.token
        )
        self.org = self.github.get_organization(config.org_name)
        self.commit_author_name = config.commit_author_name
        self.commit_author_email = config.commit_author_email
        self.source_version = config.source_version
        self.template_repo_name = config.template_repo_name
        self.config_file_name = config.config_file_name

    def get_repository(self, repo_name: str, create: bool = False, owning_team: str = None):
        """Get or create a GitHub repository with optional team permissions.

        This method attempts to retrieve a repository by name. If it doesn't exist and
        create=True, it creates a new repository. It also handles team permissions
        if an owning team is specified.

        Args:
            repo_name (str): The name of the repository to retrieve or create.
            create (bool, optional): Whether to create the repository if it doesn't exist.
            owning_team (str, optional): The name of the GitHub team to grant admin access.

        Returns:
            github.Repository.Repository: The repository object.

        Raises:
            GithubException: If repository operations fail.
        """
        try:
            try:
                repo = self.org.get_repo(repo_name)
                logger.info(f"Found existing repository: {repo_name}")
                if owning_team:
                    self.set_team_permission(repo_name, owning_team, "admin")
                return repo
            except GithubException as e:
                if e.status == 404 and create:
                    logger.info(f"Creating repository {repo_name}")
                    repo = self.org.create_repo(
                        name=repo_name,
                        private=True,
                        auto_init=True,
                        allow_squash_merge=True,
                        allow_merge_commit=True,
                        allow_rebase_merge=True,
                        delete_branch_on_merge=True
                    )
                    
                    # Wait for repository initialization
                    max_retries = 100
                    retry_delay = 1
                    for _ in range(max_retries):
                        try:
                            repo.get_branch("main")
                            break
                        except GithubException:
                            time.sleep(retry_delay)
                    else:
                        raise Exception(f"Repository {repo_name} initialization timed out")
                    
                    if owning_team:
                        self.set_team_permission(repo_name, owning_team, "admin")
                    return repo
                raise
        except GithubException as e:
            error_message = f"GitHub API error: {str(e)}"
            logger.error(error_message)
            raise

    def get_default_branch(self, repo_name: str) -> str:
        """Get the default branch name of a repository.

        Args:
            repo_name (str): Name of the repository.

        Returns:
            str: Default branch name (usually 'main' or 'master').
        """
        repo = self.org.get_repo(repo_name)
        return repo.default_branch

    def create_branch(self, repo_name: str, branch_name: str, from_ref: str = "main") -> None:
        """Create a new branch in the repository.

        Args:
            repo_name (str): Name of the repository.
            branch_name (str): Name of the branch to create.
            from_ref (str, optional): Reference to create branch from. Defaults to "main".

        Raises:
            GithubException: If branch creation fails.
        """
        repo = self.org.get_repo(repo_name)
        source = repo.get_branch(from_ref)
        
        try:
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Created branch {branch_name} in {repo_name}")
        except GithubException as e:
            error_message = f"Failed to create branch {branch_name}: {str(e)}"
            logger.error(error_message)
            raise

    def create_commit(self, repo_name: str, branch: str, commit_message: str, changes: list) -> None:
        """Create a commit with the specified changes.

        Args:
            repo_name (str): Name of the repository.
            branch (str): Branch name to commit to.
            commit_message (str): Commit message.
            changes (list): List of dictionaries with 'path' and 'content' keys.

        Raises:
            GithubException: If commit creation fails.
        """
        repo = self.org.get_repo(repo_name)
        
        try:
            # Get the branch reference
            ref = repo.get_git_ref(f"heads/{branch}")
            branch_sha = ref.object.sha
            base_tree = repo.get_git_tree(branch_sha)

            # Create tree elements
            tree_elements = []
            for change in changes:
                element = InputGitTreeElement(
                    path=change['path'],
                    mode='100644',
                    type='blob',
                    content=change['content']
                )
                tree_elements.append(element)

            # Create tree
            tree = repo.create_git_tree(tree_elements, base_tree)

            # Create commit
            parent = repo.get_git_commit(branch_sha)
            commit = repo.create_git_commit(
                message=commit_message,
                tree=tree,
                parents=[parent],
                author={"name": self.commit_author_name, "email": self.commit_author_email},
                committer={"name": self.commit_author_name, "email": self.commit_author_email}
            )

            # Update branch reference
            ref.edit(commit.sha, force=True)
            
            logger.info(f"Created commit in {repo_name}/{branch}: {commit_message}")
        except GithubException as e:
            error_message = f"Failed to create commit: {str(e)}"
            logger.error(error_message)
            raise

    def clone_repository_contents(self, source_repo: str, target_repo: str, 
                               source_ref: str = None, target_branch: str = "main") -> None:
        """Clone contents from one repository to another using PyGithub.

        Args:
            source_repo (str): Name of the source repository.
            target_repo (str): Name of the target repository.
            source_ref (str, optional): Source ref (branch/tag/SHA). Defaults to default branch.
            target_branch (str, optional): Target branch name. Defaults to "main".

        Raises:
            GithubException: If repository operations fail.
        """
        try:
            source = self.org.get_repo(source_repo)
            target = self.org.get_repo(target_repo)

            # If no source_ref specified, use the default branch
            if not source_ref:
                source_ref = source.default_branch

            # Get the tree from source repository
            if source_ref.startswith('refs/'):
                ref = source.get_git_ref(source_ref.replace('refs/', ''))
                tree_sha = ref.object.sha
            else:
                # Try as a branch first
                try:
                    branch = source.get_branch(source_ref)
                    tree_sha = branch.commit.sha
                except GithubException:
                    # If not a branch, try as a commit SHA
                    tree_sha = source_ref

            # Get the full tree
            tree = source.get_git_tree(tree_sha, recursive=True)

            # Download and create all blobs
            elements = []
            for entry in tree.tree:
                if entry.type == 'blob':
                    blob = source.get_git_blob(entry.sha)
                    content = base64.b64decode(blob.content).decode('utf-8')
                    elements.append({
                        'path': entry.path,
                        'content': content
                    })

            # Create commit with all files
            if elements:
                self.create_commit(
                    target_repo,
                    target_branch,
                    f"Clone contents from {source_repo}",
                    elements
                )
            
            logger.info(f"Successfully cloned contents from {source_repo} to {target_repo}")
        except GithubException as e:
            error_message = f"Failed to clone repository contents: {str(e)}"
            logger.error(error_message)
            raise

    def commit_repository_contents(self, repo_name: str, branch: str, contents: dict) -> None:
        """Commit multiple file contents to a repository.

        Args:
            repo_name (str): Name of the repository.
            branch (str): Branch to commit to.
            contents (dict): Dictionary mapping file paths to their content.

        Raises:
            GithubException: If commit operations fail.
        """
        try:
            # Format changes for create_commit method
            changes = [
                {'path': path, 'content': content}
                for path, content in contents.items()
            ]
            
            self.create_commit(
                repo_name=repo_name,
                branch=branch,
                commit_message="Update repository contents",
                changes=changes
            )
            
            logger.info(f"Successfully committed contents to {repo_name}/{branch}")
        except GithubException as e:
            error_message = f"Failed to commit repository contents: {str(e)}"
            logger.error(error_message)
            raise

    def update_repository_topics(self, repo_name: str, topics: list) -> None:
        """Update the topics of a repository.

        Args:
            repo_name (str): Name of the repository.
            topics (list): List of topics to set.

        Raises:
            GithubException: If the operation fails.
        """
        try:
            repo = self.org.get_repo(repo_name)
            repo.replace_topics(topics)
            logger.info(f"Updated topics for {repo_name}: {topics}")
        except GithubException as e:
            error_message = f"Failed to update repository topics: {str(e)}"
            logger.error(error_message)
            raise

    def set_team_permission(self, repo_name: str, team_name: str, permission: str) -> None:
        """Set a team's permission on a repository.

        Args:
            repo_name (str): Name of the repository.
            team_name (str): Name of the team.
            permission (str): Permission level ('pull', 'push', 'admin', 'maintain', 'triage').

        Raises:
            GithubException: If the operation fails.
        """
        try:
            repo = self.org.get_repo(repo_name)
            team = self.org.get_team_by_slug(team_name)
            team.update_team_repository(repo, permission)
            logger.info(f"Set {team_name} permission on {repo_name} to {permission}")
        except GithubException as e:
            error_message = f"Failed to set team permission: {str(e)}"
            logger.error(error_message)
            raise

    def create_pull_request(self, repo_name: str, title: str, body: str,
                          head_branch: str, base_branch: str = "main") -> None:
        """Create a pull request in a repository.

        Args:
            repo_name (str): Name of the repository.
            title (str): Title of the pull request.
            body (str): Description/body of the pull request.
            head_branch (str): Branch containing the changes.
            base_branch (str, optional): Branch to merge into. Defaults to "main".

        Returns:
            github.PullRequest.PullRequest: The created pull request object.

        Raises:
            GithubException: If pull request creation fails.
        """
        try:
            repo = self.org.get_repo(repo_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
                maintainer_can_modify=True
            )
            logger.info(f"Created PR #{pr.number} in {repo_name}: {title}")
            return pr
        except GithubException as e:
            error_message = f"Failed to create pull request: {str(e)}"
            logger.error(error_message)
            raise

    def trigger_workflow(self, repo_name: str, workflow_id: str, ref: str,
                        inputs: dict = None) -> None:
        """Trigger a GitHub Actions workflow.

        Args:
            repo_name (str): Name of the repository.
            workflow_id (str): ID or filename of the workflow.
            ref (str): Git reference to run the workflow on.
            inputs (dict, optional): Input parameters for the workflow.

        Raises:
            GithubException: If workflow dispatch fails.
        """
        try:
            repo = self.org.get_repo(repo_name)
            workflow = repo.get_workflow(workflow_id)
            
            # Convert inputs to GitHub's expected format
            workflow_inputs = inputs if inputs is not None else {}
            
            workflow.create_dispatch(
                ref=ref,
                inputs=workflow_inputs
            )
            logger.info(f"Triggered workflow {workflow_id} in {repo_name} on {ref}")
        except GithubException as e:
            error_message = f"Failed to trigger workflow: {str(e)}"
            logger.error(error_message)
            raise
