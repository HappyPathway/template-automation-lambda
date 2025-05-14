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
                try:
                    return response.json()
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON response: {response.text}")
                    return {"raw_content": response.text}
            return {}
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    # Try to parse JSON, but handle case where response is not JSON
                    if e.response.text.strip():
                        try:
                            error_body = e.response.json()
                            logger.error(f"GitHub API error details: {json.dumps(error_body)}")
                        except json.JSONDecodeError:
                            logger.error(f"GitHub API returned non-JSON error: {e.response.text}")
                    else:
                        logger.error(f"GitHub API returned empty error response with status code: {e.response.status_code}")
                except (ValueError, AttributeError):
                    logger.error(f"GitHub API error: Unable to parse response")
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
            url = f"/api/v3/repos/{self.org_name}/{repo_name}"
            repo = self._request("GET", url)
            logger.info(f"Found existing repository: {repo_name}")
            
            if owning_team:
                self.set_team_permission(repo_name, owning_team, "admin")
                
            return repo
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404 and create:
                logger.info(f"Creating repository {repo_name}")
                
                # Create a new repository with minimal parameters
                url = f"/api/v3/orgs/{self.org_name}/repos"
                try:
                    # Try with minimal parameters first
                    repo = self._request("POST", url, json={
                        "name": repo_name,
                        "private": True
                    })
                except requests.exceptions.HTTPError as create_error:
                    # Safe handling of response parsing
                    error_message = str(create_error)
                    logger.error(f"Failed to create repository with error: {error_message}")
                    
                    # If we got an HTML response instead of JSON (likely an error page)
                    if "<!DOCTYPE html>" in error_message or "<html" in error_message:
                        logger.error("Received HTML error page instead of JSON response")
                        raise Exception(f"GitHub API returned HTML error page. Your GitHub token may not have sufficient permissions or the GitHub Enterprise server might be configured differently than expected.")
                    
                    raise create_error
                
                # Now explicitly initialize the repository with a README.md file
                try:
                    logger.info(f"Initializing repository {repo_name} with a README.md file")
                    readme_content = f"# {repo_name}\n\nThis repository was created by the template automation system."
                    content_bytes = readme_content.encode("utf-8")
                    content_base64 = base64.b64encode(content_bytes).decode("utf-8")
                    
                    readme_url = f"/api/v3/repos/{self.org_name}/{repo_name}/contents/README.md"
                    readme_result = self._request("PUT", readme_url, json={
                        "message": "Initial commit with README",
                        "content": content_base64,
                        "committer": {
                            "name": self.commit_author_name,
                            "email": self.commit_author_email
                        }
                    })
                    logger.info(f"Successfully created README.md in {repo_name}")
                    
                    # Give GitHub time to process the commit and create the branch
                    time.sleep(2)
                    
                    # Now get the updated repository info
                    repo = self._request("GET", url.replace("/orgs/", "/repos/"))
                    
                    # Verify we have a default branch
                    for _ in range(3):  # Try up to 3 times
                        try:
                            default_branch = repo.get("default_branch", "main")
                            branch_info = self.get_branch(repo_name, default_branch)
                            logger.info(f"Confirmed default branch '{default_branch}' exists")
                            break
                        except requests.exceptions.HTTPError:
                            logger.info("Default branch not ready yet, waiting...")
                            time.sleep(2)
                            repo = self._request("GET", url.replace("/orgs/", "/repos/"))
                    
                except Exception as init_error:
                    logger.error(f"Failed to initialize repository: {str(init_error)}")
                    # Continue anyway since we already have the repository
                
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/branches/{branch_name}"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/git/refs"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/git/refs"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/git/refs/{ref}"
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
            url = f"/api/v3/repos/{self.org_name}/{repo_name}/contents/{path}"
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
                url = f"/api/v3/repos/{self.org_name}/{repo_name}/contents/{path}"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/contents/{path}"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/pulls"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/actions/workflows/{workflow_id}/dispatches"
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
            team_url = f"/api/v3/orgs/{self.org_name}/teams/{team_name}"
            team = self._request("GET", team_url)
            logger.info(f"Found team: {team_name}")
            
            # Try to set permissions using the correct endpoint
            # Different GitHub Enterprise versions might support different API paths
            try:
                # First try the standard endpoint
                url = f"/api/v3/orgs/{self.org_name}/teams/{team_name}/repos/{self.org_name}/{repo_name}"
                self._request("PUT", url, json={"permission": permission})
                logger.info(f"Set {team_name} permission on {repo_name} to {permission}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 422 or e.response.status_code == 404:
                    # Try alternative endpoint format for older GitHub Enterprise versions
                    try:
                        alt_url = f"/api/v3/teams/{team['id']}/repos/{self.org_name}/{repo_name}"
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
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/topics"
        
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
        url = f"/api/v3/repos/{self.org_name}/{template_repo_name}/generate"
        
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

    def create_readme_file(self, repo_name: str) -> Dict[str, Any]:
        """Create a README.md file in an empty repository to initialize it.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            The created file content data
        """
        content = f"""# {repo_name}

This repository was created automatically by the template automation system.
        """
        content_bytes = content.encode("utf-8")
        content_base64 = base64.b64encode(content_bytes).decode("utf-8")
        
        url = f"/api/v3/repos/{self.org_name}/{repo_name}/contents/README.md"
        result = self._request("PUT", url, json={
            "message": "Initialize repository with README",
            "content": content_base64,
            "committer": {
                "name": self.commit_author_name,
                "email": self.commit_author_email
            }
        })
        
        logger.info(f"Created README.md in repository {repo_name} to initialize it")
        return result["content"]

    def clone_repository_contents(
        self,
        source_repo_name: str,
        target_repo_name: str,
        source_branch: str = "main",
        target_branch: str = "main",
        commit_message: str = "Initial repository setup from template"
    ) -> None:
        """Clone all files from a source repository to a target repository.
        
        This method copies all files from the source repository to the target repository,
        effectively implementing repository templating by copying file content.
        
        Args:
            source_repo_name: Name of the source/template repository
            target_repo_name: Name of the target repository where files will be copied
            source_branch: Branch to copy files from in the source repository
            target_branch: Branch to copy files to in the target repository
            commit_message: Commit message for the file creation commits
            
        Raises:
            ValueError: If source repository or branch doesn't exist
        """
        logger.info(f"Cloning contents from {source_repo_name}:{source_branch} to {target_repo_name}:{target_branch}")
        
        # Get the source repository tree
        try:
            # Get the source repository info
            source_repo = self.get_repository(source_repo_name)
            
            # Get the branch reference
            try:
                source_branch_info = self.get_branch(source_repo_name, source_branch)
                source_commit_sha = source_branch_info["commit"]["sha"]
                logger.info(f"Using source commit SHA: {source_commit_sha}")
                
                # Get the tree recursively to get all files
                tree_url = f"/api/v3/repos/{self.org_name}/{source_repo_name}/git/trees/{source_commit_sha}?recursive=1"
                tree_data = self._request("GET", tree_url)
                
                # Filter out directories, only keep files
                files = [item for item in tree_data.get("tree", []) if item["type"] == "blob"]
                logger.info(f"Found {len(files)} files to copy from {source_repo_name}")
                
                # First ensure the target repository has the target branch
                try:
                    # Check if target branch exists
                    self.get_branch(target_repo_name, target_branch)
                    logger.info(f"Target branch {target_branch} already exists in {target_repo_name}")
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # Create README to initialize the repository with the target branch
                        logger.info(f"Creating README.md to initialize {target_repo_name} with {target_branch} branch")
                        self.create_readme_file(target_repo_name)
                        # Wait for branch to be created
                        time.sleep(2)
                        # Verify branch was created
                        try:
                            self.get_branch(target_repo_name, target_branch)
                            logger.info(f"Successfully created branch {target_branch} in {target_repo_name}")
                        except Exception as branch_err:
                            logger.error(f"Failed to verify branch creation: {str(branch_err)}")
                            raise ValueError(f"Could not initialize repository {target_repo_name} with branch {target_branch}")
                    else:
                        raise
                
                # Copy each file from source to target
                for file_item in files:
                    file_path = file_item["path"]
                    # Skip .git directory and other metadata files if they exist
                    if file_path.startswith(".git/") or file_path == ".git":
                        continue
                        
                    # Get the file content from source repo
                    try:
                        file_url = f"/api/v3/repos/{self.org_name}/{source_repo_name}/contents/{file_path}?ref={source_branch}"
                        file_data = self._request("GET", file_url)
                        
                        # GitHub API returns the content as base64
                        content = file_data.get("content", "")
                        if content:
                            # GitHub may split content with newlines, remove them
                            content = content.replace("\n", "")
                        
                        # Create the same file in target repo
                        target_url = f"/api/v3/repos/{self.org_name}/{target_repo_name}/contents/{file_path}"
                        
                        # Check if file already exists in target
                        file_exists = False
                        try:
                            existing_file = self._request("GET", f"{target_url}?ref={target_branch}")
                            file_exists = True
                            file_sha = existing_file.get("sha")
                        except requests.exceptions.HTTPError as e:
                            if e.response.status_code != 404:
                                raise
                        
                        # Setup the request payload
                        payload = {
                            "message": f"{commit_message}: {file_path}",
                            "content": content,
                            "branch": target_branch,
                            "committer": {
                                "name": self.commit_author_name,
                                "email": self.commit_author_email
                            }
                        }
                        
                        # Add SHA if updating existing file
                        if file_exists:
                            payload["sha"] = file_sha
                        
                        # Create or update the file
                        self._request("PUT", target_url, json=payload)
                        logger.info(f"Copied file {file_path} to {target_repo_name}")
                    except Exception as file_err:
                        logger.error(f"Failed to copy file {file_path}: {str(file_err)}")
                
                logger.info(f"Successfully cloned all files from {source_repo_name} to {target_repo_name}")
                return
                
            except requests.exceptions.HTTPError as branch_err:
                logger.error(f"Failed to get branch {source_branch} from {source_repo_name}: {str(branch_err)}")
                raise ValueError(f"Source branch {source_branch} does not exist in repository {source_repo_name}")
                
        except requests.exceptions.HTTPError as repo_err:
            logger.error(f"Failed to get source repository {source_repo_name}: {str(repo_err)}")
            raise ValueError(f"Source repository {source_repo_name} does not exist")
        except Exception as e:
            logger.error(f"Unexpected error during repository cloning: {str(e)}")
            raise
