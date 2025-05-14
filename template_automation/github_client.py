"""GitHub client module for template automation.

This module provides the GitHubClient class which handles all interactions with the GitHub API
for template repository automation using the requests library directly.
"""

import base64
import json
import logging
import time
import urllib.parse
from typing import List, Optional, Dict, Any, Union

import requests

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
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.token = token
        self.org_name = org_name
        self.commit_author_name = commit_author_name
        self.commit_author_email = commit_author_email
        self.verify_ssl = verify_ssl
        
        # Create session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Template-Automation-Lambda'
        })
        
        # Log initialization
        logger.info(f"Initialized GitHub client for org: {org_name} (SSL verify: {verify_ssl})")

    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the GitHub API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            url: URL path or full URL to request
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response data as a dictionary
            
        Raises:
            requests.exceptions.RequestException: On request errors
        """
        # Prepend base URL if not already an absolute URL
        if not url.startswith('http'):
            url = f"{self.api_base_url}{url}"
        
        # Set SSL verification
        kwargs['verify'] = self.verify_ssl
        
        # Log the request
        if 'json' in kwargs:
            logger.info(f"GitHub API {method} request to {url} with payload: {json.dumps(kwargs['json'])}")
        else:
            logger.info(f"GitHub API {method} request to {url}")
        
        # Make the request
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Raise exception for error status codes
            if response.status_code >= 400:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                
            response.raise_for_status()
            
            # Return JSON data for non-empty responses
            if response.text:
                return response.json()
            return {}
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"GitHub API error details: {json.dumps(error_body)}")
                except (ValueError, json.JSONDecodeError):
                    logger.error(f"GitHub API error: {e.response.text}")
            logger.error(f"Request failed: {str(e)}")
            raise

    def get_repository(
        self,
        repo_name: str,
        create: bool = False,
        owning_team: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get or create a GitHub repository with optional team permissions.
        
        Args:
            repo_name: The name of the repository to retrieve or create
            create: Whether to create the repository if it doesn't exist
            owning_team: The name of the GitHub team to grant admin access
            
        Returns:
            The repository data
        """
        try:
            # Try to get the repository
            url = f"/repos/{self.org_name}/{repo_name}"
            repo = self._request("GET", url)
            logger.info(f"Found existing repository: {repo_name}")
            
            if owning_team:
                self.set_team_permission(repo_name, owning_team, "admin")
                
            return repo
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404 and create:
                logger.info(f"Creating repository {repo_name}")
                
                # Create a new repository with minimal parameters
                url = f"/orgs/{self.org_name}/repos"
                try:
                    # Try with minimal parameters first
                    repo = self._request("POST", url, json={
                        "name": repo_name,
                        "private": False,
                        "auto_init": True
                    })
                except requests.exceptions.HTTPError as create_error:
                    # Log detailed error information for 422 errors
                    if create_error.response.status_code == 422:
                        error_response = create_error.response.json()
                        logger.error(f"GitHub API error details: {json.dumps(error_response)}")
                        # Try again with even more minimal parameters if it's a schema validation issue
                        if "message" in error_response and "Validation Failed" in error_response.get("message", ""):
                            logger.info("Retrying repository creation with minimal parameters")
                            repo = self._request("POST", url, json={
                                "name": repo_name,
                                "private": True
                            })
                        else:
                            raise
                    else:
                        raise
                
                # Wait for repository initialization
                max_retries = 10
                retry_delay = 2
                for i in range(max_retries):
                    try:
                        # Try both main and master as possible default branches
                        for branch_name in ["main", "master"]:
                            try:
                                self.get_branch(repo_name, branch_name)
                                logger.info(f"Repository initialized with default branch '{branch_name}'")
                                break
                            except requests.exceptions.HTTPError:
                                pass
                        else:
                            # If we reach here, neither branch was found, but repo may still be usable
                            if i == max_retries - 1:
                                logger.warning(f"Repository {repo_name} created but default branch not found")
                            continue
                        break
                    except requests.exceptions.HTTPError:
                        logger.info(f"Waiting for repository initialization, attempt {i+1}/{max_retries}")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                
                if owning_team:
                    try:
                        self.set_team_permission(repo_name, owning_team, "admin")
                    except requests.exceptions.HTTPError as perm_error:
                        logger.warning(f"Failed to set team permission: {str(perm_error)}")
                    
                return repo
            raise

    def get_branch(self, repo_name: str, branch_name: str) -> Dict[str, Any]:
        """Get branch information.
        
        Args:
            repo_name: Name of the repository
            branch_name: Name of the branch
            
        Returns:
            Branch data
        """
        url = f"/repos/{self.org_name}/{repo_name}/branches/{branch_name}"
        return self._request("GET", url)

    def get_default_branch(self, repo_name: str) -> str:
        """Get the default branch name of a repository.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            Default branch name (usually 'main' or 'master')
        """
        repo = self.get_repository(repo_name)
        return repo["default_branch"]

    def create_branch(self, repo_name: str, branch_name: str, from_ref: str = "main") -> None:
        """Create a new branch in the repository.
        
        Args:
            repo_name: Name of the repository
            branch_name: Name of the branch to create
            from_ref: Reference to create branch from
        """
        # Get the SHA of the source branch
        source_branch = self.get_branch(repo_name, from_ref)
        commit_sha = source_branch["commit"]["sha"]
        
        # Create the new branch
        url = f"/repos/{self.org_name}/{repo_name}/git/refs"
        self._request("POST", url, json={
            "ref": f"refs/heads/{branch_name}",
            "sha": commit_sha
        })
        
        logger.info(f"Created branch {branch_name} in {repo_name}")

    def create_reference(self, repo_name: str, ref: str, sha: str) -> None:
        """Create a Git reference.
        
        Args:
            repo_name: Name of the repository
            ref: The name of the reference
            sha: The SHA1 value to set this reference to
        """
        url = f"/repos/{self.org_name}/{repo_name}/git/refs"
        self._request("POST", url, json={
            "ref": ref,
            "sha": sha
        })
        
        logger.info(f"Created reference {ref} in {repo_name}")

    def update_reference(self, repo_name: str, ref: str, sha: str, force: bool = False) -> None:
        """Update a Git reference.
        
        Args:
            repo_name: Name of the repository
            ref: The name of the reference without 'refs/' prefix
            sha: The SHA1 value to set this reference to
            force: Force update if not a fast-forward update
        """
        url = f"/repos/{self.org_name}/{repo_name}/git/refs/{ref}"
        self._request("PATCH", url, json={
            "sha": sha,
            "force": force
        })
        
        logger.info(f"Updated reference {ref} in {repo_name}")

    def write_file(
        self,
        repo: Dict[str, Any],
        path: str,
        content: str,
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Write or update a file in a repository.
        
        Args:
            repo: The repository object
            path: Path where to create/update the file
            content: Content to write to the file
            branch: Branch to commit to
            commit_message: Commit message to use
            
        Returns:
            The created/updated file content
        """
        repo_name = repo["name"]
        content_bytes = content.encode("utf-8")
        content_base64 = base64.b64encode(content_bytes).decode("utf-8")
        
        # Try to get the existing file to check if it exists
        try:
            file = self.get_file_contents(repo_name, path, branch)
            # Update existing file
            url = f"/repos/{self.org_name}/{repo_name}/contents/{path}"
            result = self._request("PUT", url, json={
                "message": commit_message or f"Update {path}",
                "content": content_base64,
                "sha": file["sha"],
                "branch": branch,
                "committer": {
                    "name": self.commit_author_name,
                    "email": self.commit_author_email
                }
            })
            logger.info(f"Updated file {path} in repo {repo_name}")
            return result["content"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Create new file
                url = f"/repos/{self.org_name}/{repo_name}/contents/{path}"
                result = self._request("PUT", url, json={
                    "message": commit_message or f"Create {path}",
                    "content": content_base64,
                    "branch": branch,
                    "committer": {
                        "name": self.commit_author_name,
                        "email": self.commit_author_email
                    }
                })
                logger.info(f"Created new file {path} in repo {repo_name}")
                return result["content"]
            raise

    def get_file_contents(self, repo_name: str, path: str, ref: str = "main") -> Dict[str, Any]:
        """Get the contents of a file in a repository.
        
        Args:
            repo_name: Name of the repository
            path: Path to the file
            ref: Branch, tag, or commit SHA
            
        Returns:
            File data
        """
        url = f"/repos/{self.org_name}/{repo_name}/contents/{path}"
        params = {"ref": ref}
        return self._request("GET", url, params=params)

    def read_file(self, repo: Dict[str, Any], path: str, ref: str = "main") -> str:
        """Read a file from a repository.
        
        Args:
            repo: The repository object
            path: Path to the file to read
            ref: Git reference (branch, tag, commit) to read from
            
        Returns:
            The file contents as a string
        """
        repo_name = repo["name"]
        file = self.get_file_contents(repo_name, path, ref)
        content = base64.b64decode(file["content"]).decode("utf-8")
        return content

    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a pull request in a repository.
        
        Args:
            repo_name: Name of the repository
            title: Title of the pull request
            body: Description/body of the pull request
            head_branch: Branch containing the changes
            base_branch: Branch to merge into
            
        Returns:
            The created pull request object
        """
        url = f"/repos/{self.org_name}/{repo_name}/pulls"
        pr = self._request("POST", url, json={
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "maintainer_can_modify": True
        })
        
        logger.info(f"Created PR #{pr['number']} in {repo_name}: {title}")
        return pr

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
        """
        url = f"/repos/{self.org_name}/{repo_name}/actions/workflows/{workflow_id}/dispatches"
        workflow_inputs = inputs if inputs is not None else {}
        
        self._request("POST", url, json={
            "ref": ref,
            "inputs": workflow_inputs
        })
        
        logger.info(f"Triggered workflow {workflow_id} in {repo_name} on {ref}")

    def set_team_permission(self, repo_name: str, team_name: str, permission: str) -> None:
        """Set a team's permission on a repository.
        
        Args:
            repo_name: Name of the repository
            team_name: Name of the team
            permission: Permission level ('pull', 'push', 'admin', 'maintain', 'triage')
        """
        # First check if the team exists
        try:
            team_url = f"/orgs/{self.org_name}/teams/{team_name}"
            team = self._request("GET", team_url)
            logger.info(f"Found team: {team_name}")
            
            # Try to set permissions using the correct endpoint
            # Different GitHub Enterprise versions might support different API paths
            try:
                # First try the standard endpoint
                url = f"/orgs/{self.org_name}/teams/{team_name}/repos/{self.org_name}/{repo_name}"
                self._request("PUT", url, json={"permission": permission})
                logger.info(f"Set {team_name} permission on {repo_name} to {permission}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422 or e.response.status_code == 404:
                    # Try alternative endpoint format for older GitHub Enterprise versions
                    try:
                        alt_url = f"/teams/{team['id']}/repos/{self.org_name}/{repo_name}"
                        self._request("PUT", alt_url, json={"permission": permission})
                        logger.info(f"Set {team_name} permission on {repo_name} to {permission} using alternative endpoint")
                    except requests.exceptions.HTTPError as alt_e:
                        logger.error(f"Failed to set team permission using alternative endpoint: {str(alt_e)}")
                        raise
                else:
                    raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to find team {team_name}: {str(e)}")
            if e.response.status_code == 404:
                logger.warning(f"Team {team_name} not found, skipping permission assignment")
            else:
                raise

    def update_repository_topics(self, repo_name: str, topics: List[str]) -> None:
        """Update the topics of a repository.
        
        Args:
            repo_name: Name of the repository
            topics: List of topics to set
        """
        # GitHub API requires a special media type for repository topics
        headers = {"Accept": "application/vnd.github.mercy-preview+json"}
        url = f"/repos/{self.org_name}/{repo_name}/topics"
        
        self._request("PUT", url, json={"names": topics}, headers=headers)
        
        logger.info(f"Updated topics for {repo_name}: {topics}")

    def create_repository_from_template(
        self,
        template_repo_name: str,
        new_repo_name: str,
        private: bool = True,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new repository from a template.
        
        Args:
            template_repo_name: Name of the template repository
            new_repo_name: Name for the new repository
            private: Whether the new repository should be private
            description: Description for the new repository
            topics: List of topics to add to the repository
            
        Returns:
            The newly created repository
        """
        url = f"/repos/{self.org_name}/{template_repo_name}/generate"
        
        # Create repository from template
        new_repo = self._request("POST", url, json={
            "name": new_repo_name,
            "owner": self.org_name,
            "description": description or f"Repository created from template: {template_repo_name}",
            "private": private
        })
        
        # Add topics if provided
        if topics:
            self.update_repository_topics(new_repo_name, topics)
            
        logger.info(f"Created new repository: {new_repo_name} from template: {template_repo_name}")
        return new_repo
