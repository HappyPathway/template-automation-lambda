####################################################################################
# This Lambda function takes JSON input and writes it directly to a config.json file
# in a cloned GitHub repository. The changes are then committed and pushed to the 
# GitHub API, creating a new repository for the EKS CI/CD pipeline.
# This implementation uses only pure Python with requests library (no Git CLI dependency).
####################################################################################

import os
import stat
import shutil
import logging
import base64
import time
import requests
import json
from urllib.parse import urlparse
from datetime import datetime
import traceback

import boto3
from botocore.exceptions import ClientError

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")  # Set to "ERROR" to reduce logging messages.

# Get environment variables
SECRET_NAME = os.environ["SECRET_NAME"]

class GitHubClient:
    """A class to interact with GitHub API without relying on external Git binaries.
    
    This class encapsulates all GitHub API operations for managing repositories,
    branches, files, commits and other Git operations using only the requests library.
    """
    
    def __init__(self, api_base_url, token, org_name, commit_author_name, commit_author_email, source_version=None, template_repo_name=None, config_file_name="config.json"):
        """Initialize the GitHub client
        
        Args:
            api_base_url (str): Base URL for the GitHub API
            token (str): GitHub access token
            org_name (str): GitHub organization name
            commit_author_name (str): Name of the commit author
            commit_author_email (str): Email of the commit author
            source_version (str, optional): Version to use from template repo
            template_repo_name (str, optional): Name of the template repository
            config_file_name (str, optional): Name of the config file to write
        """
        self.api_base_url = api_base_url
        self.token = token
        self.org_name = org_name
        self.commit_author_name = commit_author_name
        self.commit_author_email = commit_author_email
        self.source_version = source_version
        self.template_repo_name = template_repo_name
        self.config_file_name = config_file_name
        self.headers = self._create_headers()
        
    def _create_headers(self):
        """Create headers for GitHub API requests
        
        Returns:
            dict: Headers for GitHub API requests
        """
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
    def get_repository(self, repo_name, create=False):
        """Get or create a repository
        
        Args:
            repo_name (str): Name of the repository
            create (bool, optional): Create the repository if it doesn't exist
            
        Returns:
            dict: Repository information from GitHub API
        """
        get_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}"
        try:
            response = requests.get(get_url, headers=self.headers, verify=False)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404 and create:
                logger.info(f"Creating repository {repo_name}")
                create_url = f"{self.api_base_url}/orgs/{self.org_name}/repos"
                repo_data = {
                    "name": repo_name,
                    "private": True,
                    "auto_init": True,  # Initialize with README
                    "default_branch": "main",
                    "allow_squash_merge": True,
                    "allow_merge_commit": True,
                    "allow_rebase_merge": True,
                    "delete_branch_on_merge": True,
                    "enable_branch_protection": False  # Disable branch protection
                }
                create_response = requests.post(
                    create_url, 
                    headers=self.headers, 
                    json=repo_data,
                    verify=False
                )
                
                if create_response.status_code in (201, 200):
                    # Wait for repository initialization
                    repo = create_response.json()
                    max_retries = 100
                    retry_delay = 1
                    for _ in range(max_retries):
                        try:
                            # Try to get the main branch's reference
                            self.get_reference_sha(repo_name, "heads/main")
                            return repo
                        except Exception:
                            # If reference doesn't exist yet, wait and retry
                            time.sleep(retry_delay)
                            continue
                    # If we got here, initialization failed
                    raise Exception(f"Repository {repo_name} initialization timed out")
                else:
                    error_message = f"Failed to create repository: {create_response.status_code} - {create_response.text}"
                    logger.error(error_message)
                    raise Exception(error_message)
            else:
                error_message = f"Repository {repo_name} not found and create=False"
                logger.error(error_message)
                raise Exception(error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"Error accessing GitHub API: {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def get_default_branch(self, repo_name):
        """Get the default branch of a repository
    
        Args:
            repo_name (str): Name of the repository
        
        Returns:
            str: Default branch name
        """
        repo_api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}"
        response = requests.get(repo_api_url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            repo_info = response.json()
            return repo_info["default_branch"]
        else:
            error_message = f"Failed to get default branch for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)

    def get_reference_sha(self, repo_name, ref):
        """Get the SHA for a reference (branch, tag, etc)
    
        Args:
            repo_name (str): Name of the repository
            ref (str): Reference name (e.g., 'heads/main')
    
        Returns:
            str: SHA of the reference
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/refs/{ref}"
        response = requests.get(api_url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            ref_info = response.json()
            return ref_info["object"]["sha"]
        else:
            error_message = f"Failed to get reference {ref} for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)

    def get_commit(self, repo_name, commit_sha):
        """Get a commit by SHA
    
        Args:
            repo_name (str): Name of the repository
            commit_sha (str): Commit SHA
    
        Returns:
            dict: Commit information
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/commits/{commit_sha}"
        response = requests.get(api_url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to get commit {commit_sha} for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def get_tree(self, repo_name, tree_sha, recursive=False):
        """Get a tree by SHA
    
        Args:
            repo_name (str): Name of the repository
            tree_sha (str): Tree SHA
            recursive (bool): Whether to get the tree recursively
    
        Returns:
            dict: Tree information
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/trees/{tree_sha}"
        if recursive:
            api_url += "?recursive=1"
            
        response = requests.get(api_url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to get tree {tree_sha} for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def download_repository_files(self, repo_name, tree, target_dir):
        """Download all files from a repository tree to a local directory
    
        Args:
            repo_name (str): Name of the repository
            tree (dict): Tree information from get_tree()
            target_dir (str): Directory to download files to
        """
        # Ensure target directory exists even if there are no files
        os.makedirs(target_dir, exist_ok=True)
        
        for item in tree.get("tree", []):
            if item["type"] == "blob":
                # Get the blob contents
                blob_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/blobs/{item['sha']}"
                blob_response = requests.get(blob_url, headers=self.headers, verify=False)
                
                if blob_response.status_code == 200:
                    blob_data = blob_response.json()
                    content = None
                    
                    # Ensure the target directory exists
                    file_path = os.path.join(target_dir, item["path"])
                    dir_path = os.path.dirname(file_path)
                    os.makedirs(dir_path, exist_ok=True)
                    
                    # GitHub API returns base64 encoded content
                    if blob_data.get("encoding") == "base64":
                        content = base64.b64decode(blob_data.get("content", ""))
                    else:
                        # Handle non-base64 content if needed
                        logger.warning(f"Unexpected encoding for blob {item['sha']}: {blob_data.get('encoding')}")
                        
                    if content is not None:
                        logger.info(f"Writing file to {file_path}")
                        with open(file_path, "wb") as f:
                            f.write(content)
    
    def create_blob(self, repo_name, content):
        """Create a blob in the repository
    
        Args:
            repo_name (str): Name of the repository
            content (bytes): Content of the blob
    
        Returns:
            str: SHA of the created blob
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/blobs"
        
        # Base64 encode the content
        content_b64 = base64.b64encode(content).decode('utf-8')
        
        data = {
            "content": content_b64,
            "encoding": "base64"
        }
        
        response = requests.post(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code in (201, 200):
            return response.json()["sha"]
        else:
            error_message = f"Failed to create blob for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def create_tree(self, repo_name, tree_items, base_tree_sha=None):
        """Create a tree in the repository
    
        Args:
            repo_name (str): Name of the repository
            tree_items (list): List of tree items (path, mode, type, sha)
            base_tree_sha (str): SHA of the base tree (optional)
    
        Returns:
            str: SHA of the created tree
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/trees"
        
        data = {
            "tree": tree_items
        }
        
        if base_tree_sha:
            data["base_tree"] = base_tree_sha
        
        response = requests.post(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code in (201, 200):
            return response.json()["sha"]
        else:
            error_message = f"Failed to create tree for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def create_commit(self, repo_name, message, tree_sha, parent_shas):
        """Create a commit in the repository
    
        Args:
            repo_name (str): Name of the repository
            message (str): Commit message
            tree_sha (str): SHA of the tree
            parent_shas (list): List of parent commit SHAs
    
        Returns:
            str: SHA of the created commit
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/commits"
        
        # Add committer/author information
        current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        author_info = {
            "name": self.commit_author_name,
            "email": self.commit_author_email,
            "date": current_time
        }
        
        data = {
            "message": message,
            "tree": tree_sha,
            "parents": parent_shas,
            "author": author_info,
            "committer": author_info
        }
        
        response = requests.post(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code in (201, 200):
            return response.json()["sha"]
        else:
            error_message = f"Failed to create commit for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def update_reference(self, repo_name, ref, sha):
        """Update a reference in the repository
    
        Args:
            repo_name (str): Name of the repository
            ref (str): Reference name (e.g., 'heads/main')
            sha (str): SHA to update the reference to
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/refs/{ref}"
        
        data = {
            "sha": sha,
            "force": True
        }
        
        response = requests.patch(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code not in (200, 201):
            error_message = f"Failed to update reference {ref} for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
    
    def create_reference(self, repo_name, ref, sha):
        """Create a reference in the repository
    
        Args:
            repo_name (str): Name of the repository
            ref (str): Full reference name (e.g., 'refs/heads/main')
            sha (str): SHA to create the reference at
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/git/refs"
        
        data = {
            "ref": ref,
            "sha": sha
        }
        
        response = requests.post(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code not in (201, 200):
            error_message = f"Failed to create reference {ref} for {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
            
    def clone_repository_contents(self, source_repo, target_dir, branch=None):
        """Clone a repository's contents to a local directory using GitHub API

        Args:
            source_repo (str): Name of the source repository
            target_dir (str): Target directory to download files to
            branch (str, optional): Branch to clone from. If None, uses default branch.

        Returns:
            str: The branch name that was cloned
        """
        # Create the target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        try:
            if branch:
                target_branch = branch
                # Try to get the branch's reference directly
                tree_sha = self.get_reference_sha(source_repo, f"heads/{target_branch}")
            else:
                # If no branch specified, use default branch
                target_branch = self.get_default_branch(source_repo)
                tree_sha = self.get_reference_sha(source_repo, f"heads/{target_branch}")
        except Exception as e:
            logger.warning(f"Failed to get reference for {branch or 'default branch'}: {str(e)}")
            target_branch = branch or "main"
            # If we can't get the reference, the branch might not exist yet
            tree = {"tree": []}
            self.download_repository_files(source_repo, tree, target_dir)
            return target_branch

        # Get the full tree for the branch
        logger.info(f"Getting file tree from {source_repo} for branch {target_branch}")
        tree = self.get_tree(source_repo, tree_sha, recursive=True)

        # Download all files
        logger.info(f"Downloading all files from {source_repo} using ref: heads/{target_branch}")
        self.download_repository_files(source_repo, tree, target_dir)

        return target_branch
    
    def commit_repository_contents(self, repo_name, work_dir, commit_message, branch=None):
        """Commit all files from a directory to a repository

        Args:
            repo_name (str): Name of the repository
            work_dir (str): Directory containing the files to commit
            commit_message (str): Commit message
            branch (str, optional): Branch to commit to. If None, uses default branch.

        Returns:
            str: The branch name that was committed to
        """
        # First, get the current state of the target repository
        try:
            target_branch = branch or self.get_default_branch(repo_name)
        except Exception:
            # If we can't get the default branch, it might be a new repo
            target_branch = branch or "main"
        
        # Upload all files to the repository
        tree_items = []
        
        # Add all files from the work directory to the repository
        for root, _, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                repo_path = os.path.relpath(file_path, work_dir)
                
                # Skip .git directory if it exists
                if ".git" in repo_path.split(os.path.sep):
                    continue
                    
                # Read file content
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    
                # Create blob for the file
                blob_sha = self.create_blob(repo_name, file_content)
                
                # Add to tree items
                tree_items.append({
                    "path": repo_path,
                    "mode": "100644",  # Regular file
                    "type": "blob",
                    "sha": blob_sha
                })
        
                # Try to get the latest commit SHA from the base branch
                base_branch = "main"  # Always use main as base when creating new branches
                try:
                    base_commit_sha = self.get_reference_sha(repo_name, f"heads/{base_branch}")
                    base_commit = self.get_commit(repo_name, base_commit_sha)
                    base_tree_sha = base_commit["tree"]["sha"]
                except Exception:
                    # If we can't get the reference, assume it's a new repo with no commits
                    base_tree_sha = None

        # Create a new tree with all the files
        new_tree_sha = self.create_tree(repo_name, tree_items, base_tree_sha)
        
        # Create a commit with the new tree
        if base_tree_sha:
            # If we have a base tree, include the parent commit
            new_commit_sha = self.create_commit(
                repo_name, 
                commit_message,
                new_tree_sha,
                [base_commit_sha]
            )
        else:
            # If it's a new repo, create the first commit
            new_commit_sha = self.create_commit(
                repo_name,
                commit_message,
                new_tree_sha,
                []
            )
        
        # Update or create the reference to point to the new commit
        try:
            # Try to update existing branch
            self.update_reference(
                repo_name,
                f"heads/{target_branch}",
                new_commit_sha
            )
        except Exception:
            # If the branch doesn't exist, create it
            try:
                self.create_reference(
                    repo_name,
                    f"refs/heads/{target_branch}",
                    new_commit_sha
                )
            except Exception as e:
                # If we still can't create the branch, something is wrong
                error_message = f"Failed to create or update branch {target_branch} for {repo_name}: {str(e)}"
                logger.error(error_message)
                raise Exception(error_message)
        
        return target_branch


# pylint: disable=unused-argument
def lambda_handler(event, context):
    """Main Lambda handler function

    Args:
        event (dict): Dict containing the Lambda function event data
        context (dict): Lambda runtime context

    Returns:
        dict: Dict containing status message
    """
    logger.info(f"Lambda function invoked with RequestId: {context.aws_request_id}")
    logger.info(f"Remaining time in milliseconds: {context.get_remaining_time_in_millis()}")
    logger.info(f"Received event: {json.dumps(event, indent=2)}")

    input_data = event["body"]
    logger.info(f"Extracted input data from event body: {json.dumps(input_data, indent=2)}")

    project_name = input_data["project_name"]
    eks_settings = input_data["eks_settings"]
    logger.info(f"Project name: {project_name}")
    logger.info(f"EKS settings to be applied: {json.dumps(eks_settings, indent=2)}")

    if not project_name:
        logger.error("Missing project name in input")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing project name"})
        }

    try:
        logger.info(f"Starting GitHub operations for project: {project_name}")
        operate_github(project_name, eks_settings)
        logger.info("GitHub operations completed successfully")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error in operate_github: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    logger.info("Lambda execution completed successfully")
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"result": "Success"})
    }

def operate_github(new_repo_name, eks_settings):
    """Write EKS settings to config.json and create/update repository using GitHub API

    This implementation uses only the requests library and does not rely on git CLI
    or any external binaries.

    Args:
        new_repo_name (str): Name of the new GitHub repo
        eks_settings (json): Input JSON data with all the EKS parameter values

    Returns:
        None
    """
    logger.info("Starting GitHub repository operation")
    logger.info(f"Target repository name: {new_repo_name}")

    token = github_token()
    logger.info("Successfully retrieved GitHub token from Secrets Manager")

    github_api = os.environ.get("GITHUB_API")  # No default - must be configured
    org_name = os.environ.get("GITHUB_ORG_NAME")  # No default - must be configured
    commit_author_email = os.environ.get("GITHUB_COMMIT_AUTHOR_EMAIL", "eks-automation@example.com")
    commit_author_name = os.environ.get("GITHUB_COMMIT_AUTHOR_NAME", "EKS Automation Lambda")
    source_version = os.environ.get("TEMPLATE_SOURCE_VERSION")  # Optional
    template_repo_name = os.environ.get("TEMPLATE_REPO_NAME", "template-eks-cluster")
    config_file_name = "config.json"
    
    # Create work directory if it doesn't exist
    work_dir = f"/tmp/{new_repo_name}"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=False, onerror=remove_readonly)
    os.makedirs(work_dir, exist_ok=True)
    
    # Initialize GitHub client with all required parameters
    github = GitHubClient(
        github_api,
        token,
        org_name,
        commit_author_name,
        commit_author_email,
        source_version,
        template_repo_name,
        config_file_name
    )
    
    # Get info about original repo
    logger.info(f"Fetching original repository information: {template_repo_name}")
    orig_repo = github.get_repository(template_repo_name)
    
    # Get or create the new repository
    logger.info(f"Getting or creating repository: {new_repo_name}")
    new_repo = github.get_repository(new_repo_name, create=True)
    
    # Clone the original repository contents
    github.clone_repository_contents(template_repo_name, work_dir)
    
    # Write EKS settings directly to config.json
    output_file_path = os.path.join(work_dir, config_file_name)
    logger.info(f"Writing EKS settings to {output_file_path}")
    with open(output_file_path, "w") as file:
        json.dump(eks_settings, file, indent=2)
    
    # Commit all files to the new repository's main branch explicitly
    commit_message = "Add the EKS configuration file by the Lambda function"
    github.commit_repository_contents(new_repo_name, work_dir, commit_message, branch="main")
    logger.info(f"Successfully updated {new_repo_name} repository")

def github_token():
    """Retrieve GitHub access token from AWS Secrets Manager
    
    Returns:
        str: The GitHub access token.
    """
    secrets = boto3.client("secretsmanager")
    try:
        secret = secrets.get_secret_value(SecretId=SECRET_NAME)
        return secret["SecretString"]
    except ClientError as e:
        logger.error(f"Error occurred when retrieving GitHub token from Secrets Manager: {str(e)}")
        raise

def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal.
    This function is used by `shutil.rmtree` function.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)
