"""GitHub client module for template automation.

This module provides the GitHubClient class which handles all interactions with the GitHub API
for template repository automation.
"""

import base64
import logging
import time
from typing import List, Optional, Dict, Any, Union

from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile
from github.Organization import Organization
from github.Team import Team
from github.PullRequest import PullRequest
from github.Workflow import Workflow

logger = logging.getLogger(__name__)

class GitHubClient:
    """A client for interacting with GitHub's API in the context of template automation.
    
    This class provides methods for template repository operations including:
    - Creating repositories from templates
    - Managing repository contents
    - Setting up team access
    - Configuring repository settings
    
    Attributes:
        api_base_url (str): Base URL for the GitHub API
        token (str): GitHub authentication token
        org_name (str): GitHub organization name
        commit_author_name (str): Name to use for automated commits
        commit_author_email (str): Email to use for automated commits
        client (Github): PyGithub client instance
        org (Organization): GitHub organization instance
        verify_ssl (bool): Whether to verify SSL certificates
    
    Example:
        ```python
        client = GitHubClient(
            api_base_url="https://api.github.com",
            token="ghp_...",
            org_name="my-org",
            commit_author_name="Template Bot",
            commit_author_email="bot@example.com"
        )
        
        repo = client.create_repository_from_template(
            template_repo_name="template-service",
            new_repo_name="new-service",
            private=True
        )
        ```
    """

    def __init__(
        self, 
        api_base_url: str,
        token: str,
        org_name: str,
        commit_author_name: str = "Template Automation",
        commit_author_email: str = "automation@example.com",
        verify_ssl: bool = True
    ):
        """Initialize a new GitHub client.
        
        Args:
            api_base_url: Base URL for the GitHub API
            token: GitHub authentication token
            org_name: GitHub organization name
            commit_author_name: Name to use for automated commits
            commit_author_email: Email to use for automated commits
            verify_ssl: Whether to verify SSL certificates
            
        Raises:
            GithubException: If authentication fails or org doesn't exist
        """
        self.api_base_url = api_base_url
        self.token = token
        self.org_name = org_name
        self.commit_author_name = commit_author_name
        self.commit_author_email = commit_author_email
        self.verify_ssl = verify_ssl
        
        # Set environment variable for PyGithub to allow any hostname (for enterprise GitHub)
        # This is needed before initializing the client
        import os
        os.environ["GITHUB_ALLOW_HOSTNAME"] = "TRUE"
        
        try:
            # Try to use modern auth approach if available
            from github import Auth
            auth = Auth.Token(token)
            self.client = Github(
                auth=auth,
                base_url=api_base_url,
                verify=verify_ssl,
                per_page=100,  # Optimize API call efficiency
                timeout=30,    # Set a reasonable timeout
                retry=10       # Enable retries for transient issues
            )
        except ImportError:
            # Fall back to older authentication method if Auth module isn't available
            self.client = Github(
                login_or_token=token,
                base_url=api_base_url, 
                verify=verify_ssl,
                per_page=100,  # Optimize API call efficiency
                timeout=30,    # Set a reasonable timeout
            )
        
        try:
            self.org = self.client.get_organization(org_name)
            logger.info(f"Initialized GitHub client for org: {org_name} (SSL verify: {verify_ssl})")
        except GithubException as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            raise

    def create_repository_from_template(
        self,
        template_repo_name: str,
        new_repo_name: str,
        private: bool = True,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> Repository:
        """Create a new repository from a template.
        
        Args:
            template_repo_name: Name of the template repository
            new_repo_name: Name for the new repository
            private: Whether the new repository should be private
            description: Description for the new repository
            topics: List of topics to add to the repository
            
        Returns:
            The newly created repository
            
        Raises:
            GithubException: If template doesn't exist or repo creation fails
        """
        template_repo = self.org.get_repo(template_repo_name)
        
        # Create repository from template
        new_repo = self.org.create_repository_from_template(
            name=new_repo_name,
            template_repository=template_repo,
            private=private,
            description=description or f"Repository created from template: {template_repo_name}"
        )
        
        # Add topics if provided
        if topics:
            new_repo.replace_topics(topics)
            
        logger.info(f"Created new repository: {new_repo_name} from template: {template_repo_name}")
        return new_repo

    def set_team_access(self, repo: Repository, team_slug: str, permission: str = "admin") -> None:
        """Give a team access to a repository.
        
        Args:
            repo: The repository to grant access to
            team_slug: The team's slug identifier
            permission: The permission level to grant (pull, push, admin)
            
        Raises:
            GithubException: If team doesn't exist or permission grant fails
        """
        try:
            team = self.org.get_team_by_slug(team_slug)
            team.add_to_repos(repo)
            team.set_repo_permission(repo, permission)
            logger.info(f"Granted {permission} access to team {team_slug} for repo {repo.name}")
        except GithubException as e:
            logger.error(f"Failed to set team access: {e}")
            raise

    def write_file(
        self,
        repo: Repository,
        path: str,
        content: str,
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> ContentFile:
        """Write or update a file in a repository.
        
        Args:
            repo: The repository to write to
            path: Path where to create/update the file
            content: Content to write to the file
            branch: Branch to commit to
            commit_message: Commit message to use
            
        Returns:
            The created/updated file content
            
        Raises:
            GithubException: If file operation fails
        """
        try:
            # Convert content to base64
            content_bytes = content.encode("utf-8")
            content_base64 = base64.b64encode(content_bytes).decode("utf-8")
            
            # Try to get existing file
            try:
                file = repo.get_contents(path, ref=branch)
                # Update existing file
                result = repo.update_file(
                    path=path,
                    message=commit_message or f"Update {path}",
                    content=content_base64,
                    sha=file.sha,
                    branch=branch,
                    committer={
                        "name": self.commit_author_name,
                        "email": self.commit_author_email
                    }
                )
                logger.info(f"Updated file {path} in repo {repo.name}")
                return result["content"]
            except GithubException as e:
                if e.status != 404:  # Only handle "not found" errors
                    raise
                
                # Create new file
                result = repo.create_file(
                    path=path,
                    message=commit_message or f"Create {path}",
                    content=content_base64,
                    branch=branch,
                    committer={
                        "name": self.commit_author_name,
                        "email": self.commit_author_email
                    }
                )
                logger.info(f"Created new file {path} in repo {repo.name}")
                return result["content"]
                
        except GithubException as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise

    def read_file(
        self,
        repo: Repository,
        path: str,
        ref: str = "main"
    ) -> str:
        """Read a file from a repository.
        
        Args:
            repo: The repository to read from
            path: Path to the file to read
            ref: Git reference (branch, tag, commit) to read from
            
        Returns:
            The file contents as a string
            
        Raises:
            GithubException: If file doesn't exist or read fails
        """
        try:
            file = repo.get_contents(path, ref=ref)
            content = base64.b64decode(file.content).decode("utf-8")
            return content
        except GithubException as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise

    def get_repository(
        self,
        repo_name: str,
        create: bool = False,
        owning_team: Optional[str] = None
    ) -> Repository:
        """Get or create a GitHub repository with optional team permissions.
        
        Args:
            repo_name: The name of the repository to retrieve or create
            create: Whether to create the repository if it doesn't exist
            owning_team: The name of the GitHub team to grant admin access
            
        Returns:
            The repository object
            
        Raises:
            GithubException: If repository operations fail
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
            repo_name: Name of the repository
            
        Returns:
            Default branch name (usually 'main' or 'master')
        """
        repo = self.org.get_repo(repo_name)
        return repo.default_branch

    def create_branch(self, repo_name: str, branch_name: str, from_ref: str = "main") -> None:
        """Create a new branch in the repository.
        
        Args:
            repo_name: Name of the repository
            branch_name: Name of the branch to create
            from_ref: Reference to create branch from
            
        Raises:
            GithubException: If branch creation fails
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

    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Any:
        """Create a pull request in a repository.
        
        Args:
            repo_name: Name of the repository
            title: Title of the pull request
            body: Description/body of the pull request
            head_branch: Branch containing the changes
            base_branch: Branch to merge into
            
        Returns:
            The created pull request object
            
        Raises:
            GithubException: If pull request creation fails
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

    def trigger_workflow(
        self,
        repo_name: str,
        workflow_id: str,
        ref: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> None:
        """Trigger a GitHub Actions workflow.
        
        Args:
            repo_name: Name of the repository
            workflow_id: ID or filename of the workflow
            ref: Git reference to run the workflow on
            inputs: Input parameters for the workflow
            
        Raises:
            GithubException: If workflow dispatch fails
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

    def set_team_permission(self, repo_name: str, team_name: str, permission: str) -> None:
        """Set a team's permission on a repository.
        
        Args:
            repo_name: Name of the repository
            team_name: Name of the team
            permission: Permission level ('pull', 'push', 'admin', 'maintain', 'triage')
            
        Raises:
            GithubException: If the operation fails
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

    def update_repository_topics(self, repo_name: str, topics: List[str]) -> None:
        """Update the topics of a repository.
        
        Args:
            repo_name: Name of the repository
            topics: List of topics to set
            
        Raises:
            GithubException: If the operation fails
        """
        try:
            repo = self.org.get_repo(repo_name)
            repo.replace_topics(topics)
            logger.info(f"Updated topics for {repo_name}: {topics}")
        except GithubException as e:
            error_message = f"Failed to update repository topics: {str(e)}"
            logger.error(error_message)
            raise
