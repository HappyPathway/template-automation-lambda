####################################################################################
# This Lambda function takes JSON input, processes it using a Jinja2 template,
# and writes the output to a file in a cloned GitHub repository.
# The changes are then committed and pushed to the Census GitHub Enterprise Server,
# creating a new repository for the Census EKS CI/CD pipeline.
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
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
import os


# Get configuration from environment variables with defaults
CENSUS_GITHUB_API = os.environ.get("CENSUS_GITHUB_API", "https://github.e.it.census.gov/api/v3")
ORG_NAME = os.environ.get("GITHUB_ORG_NAME", "SCT-Engineering")
SECRET_NAME = os.environ.get("GITHUB_TOKEN_SECRET_NAME", "/eks-cluster-deployment/github_token")

ORIG_REPO_NAME = os.environ.get("TEMPLATE_REPO_NAME", "template-eks-cluster")

TEMPLATE_FILE_NAME = os.environ.get("TEMPLATE_FILE_NAME", "eks.hcl.j2")
HCL_FILE_NAME = os.environ.get("HCL_FILE_NAME", "eks.hcl")

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")  # Set to "ERROR" to reduce logging messages.


class GitHubClient:
    """A class to interact with GitHub API without relying on external Git binaries.
    
    This class encapsulates all GitHub API operations for managing repositories,
    branches, files, commits and other Git operations using only the requests library.
    """
    
    def __init__(self, api_base_url, token, org_name):
        """Initialize the GitHub client
        
        Args:
            api_base_url (str): Base URL for the GitHub API
            token (str): GitHub access token
            org_name (str): GitHub organization name
        """
        self.api_base_url = api_base_url
        self.token = token
        self.org_name = org_name
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
        """Get or create a repository in the GitHub organization
    
        Args:
            repo_name (str): Name of the repository
            create (bool): Whether to create the repo if it doesn't exist
    
        Returns:
            dict: Repository information
        """
        repo_api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}"
        
        # Try to get the repository
        logger.info(f"Checking if repository {repo_name} exists")
        response = requests.get(repo_api_url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            # Repository exists
            return response.json()
        elif response.status_code == 404 and create:
            # Repository doesn't exist, create it
            logger.info(f"Creating repository {repo_name}")
            create_url = f"{self.api_base_url}/orgs/{self.org_name}/repos"
            repo_data = {
                "name": repo_name,
                "description": "EKS Automation CI/CD Pipeline Repo",
                "private": True,
                "visibility": "internal"
            }
            create_response = requests.post(
                create_url, 
                headers=self.headers, 
                json=repo_data,
                verify=False
            )
            
            if create_response.status_code in (201, 200):
                return create_response.json()
            else:
                error_message = f"Failed to create repository: {create_response.status_code} - {create_response.text}"
                logger.error(error_message)
                raise Exception(error_message)
        else:
            error_message = f"Repository {repo_name} not found and create=False"
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
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # GitHub API returns base64 encoded content
                    if blob_data.get("encoding") == "base64":
                        content = base64.b64decode(blob_data.get("content", ""))
                        
                    if content is not None:
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
        
        data = {
            "message": message,
            "tree": tree_sha,
            "parents": parent_shas
        }
        
        # Add committer/author information
        current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        data["author"] = {
            "name": "EKS Automation Lambda",
            "email": "eks-automation@census.gov",
            "date": current_time
        }
        data["committer"] = data["author"]
        
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
            
    def clone_repository_contents(self, source_repo, target_dir):
        """Clone a repository's contents to a local directory using GitHub API
        
        Args:
            source_repo (str): Name of the source repository
            target_dir (str): Target directory to download files to
            
        Returns:
            str: The default branch name of the repository
        """
        # Get default branch of original repo
        default_branch = self.get_default_branch(source_repo)
        logger.info(f"Default branch for {source_repo}: {default_branch}")
        
        # Get tree from original repository
        logger.info(f"Getting file tree from {source_repo}")
        tree_sha = self.get_reference_sha(source_repo, f"heads/{default_branch}")
        tree = self.get_tree(source_repo, tree_sha, recursive=True)
        
        # Download all files from original repo to work directory
        logger.info(f"Downloading all files from {source_repo}")
        self.download_repository_files(source_repo, tree, target_dir)
        
        return default_branch
    
    def commit_repository_contents(self, repo_name, work_dir, commit_message):
        """Commit all files from a directory to a repository
        
        Args:
            repo_name (str): Name of the repository
            work_dir (str): Directory containing the files to commit
            commit_message (str): Commit message
            
        Returns:
            str: The default branch name of the repository
        """
        # First, get the current state of the target repository
        try:
            target_default_branch = self.get_default_branch(repo_name)
        except Exception:
            # If we can't get the default branch, it might be a new repo
            target_default_branch = "main"
        
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
        
        # Try to get the latest commit SHA for the branch
        # If it doesn't exist, we'll create it
        try:
            latest_commit_sha = self.get_reference_sha(repo_name, f"heads/{target_default_branch}")
            latest_commit = self.get_commit(repo_name, latest_commit_sha)
            base_tree_sha = latest_commit["tree"]["sha"]
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
                [latest_commit_sha]
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
            self.update_reference(
                repo_name, 
                f"heads/{target_default_branch}", 
                new_commit_sha
            )
        except Exception:
            # If the reference doesn't exist, create it
            self.create_reference(
                repo_name, 
                f"refs/heads/{target_default_branch}", 
                new_commit_sha
            )
        
        return target_default_branch


# pylint: disable=unused-argument
def lambda_handler(event, context):
    """
    Main Lambda handler function

    Args:
        event (dict): Dict containing the Lambda function event data.
        context (dict): Lambda runtime context.

    Returns:
        dict: Dict containing status message.
    """

    # For test, load input data from a local file.
    # input_data = ""
    # with open("data.json", "r") as file:
    #     input_data = json.load(file)

    input_data = json.loads(event["body"])

    project_name = input_data["project_name"]
    eks_settings = input_data["eks_settings"]
    if not project_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing project name"}),
        }

    try:
        rendered = operate_github(project_name, eks_settings, HCL_FILE_NAME)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error in operate_github: {str(e)}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"result": rendered}),
    }


def operate_github(new_repo_name, eks_settings, output_hcl):
    """Process template and create/update repository using GitHub API
    
    This implementation uses only the requests library and does not rely on git CLI
    or any external binaries.

    Args:
        new_repo_name (str): Name of the new GitHub repo.
        eks_settings (json): Input JSON data with all the EKS parameter values.
        output_hcl (str): Name of the EKS parameter file in HCL format.

    Returns:
        str: The rendered EKS parameter string.
    """

    # Get GitHub access token
    token = github_token()
    
    # Create work directory if it doesn't exist
    work_dir = f"/tmp/{new_repo_name}"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=False, onerror=remove_readonly)
    os.makedirs(work_dir, exist_ok=True)
    
    # Initialize GitHub client
    github = GitHubClient(CENSUS_GITHUB_API, token, ORG_NAME)
    
    # Get info about original repo
    logger.info(f"Fetching original repository information: {ORIG_REPO_NAME}")
    orig_repo = github.get_repository(ORIG_REPO_NAME)
    
    # Get or create the new repository
    logger.info(f"Getting or creating repository: {new_repo_name}")
    new_repo = github.get_repository(new_repo_name, create=True)
    
    # Clone the original repository contents
    github.clone_repository_contents(ORIG_REPO_NAME, work_dir)
    
    # Render the template and write to file
    rendered = render_j2_template(eks_settings, TEMPLATE_FILE_NAME)
    output_file_path = os.path.join(work_dir, output_hcl)
    
    logger.info(f"Writing rendered template to {output_file_path}")
    with open(output_file_path, "w") as file:
        file.write(rendered)
    
    # Commit all files to the new repository
    commit_message = "Add the EKS parameter file by the Lambda function"
    github.commit_repository_contents(new_repo_name, work_dir, commit_message)
    
    logger.info(f"Successfully updated {new_repo_name} repository")
    return rendered


def render_j2_template(eks_settings, j2_template, j2_template_dir="templates/"):
    """Render the j2 template with the input JSON data

    Args:
        eks_settings (json): input data in JSON format.
        j2_template (j2): Name of the template file to generate the output.
        j2_template_dir (str, optional): The directory where the templates are stored. Defaults to "templates/".

    Returns:
        str: Rendered template string.
    """

    # Render template
    jinja_env = Environment(loader=FileSystemLoader(j2_template_dir), trim_blocks=True)
    template = jinja_env.get_template(j2_template)

    return template.render(data=eks_settings)


def github_token():
    """Retrieve GitHub access token from AWS SSM Parameter store

    Returns:
        str: The GitHub access token.
    """
    ssm = boto3.client("ssm")
    try:
        token = ssm.get_parameter(Name=SECRET_NAME, WithDecryption=True)["Parameter"][
            "Value"
        ]
    except ClientError:
        logger.error("Error occurred when retrieving GitHub token from SSM Parameter")
        raise

    return token


def remove_readonly(func, path, _):
    """
    Clear the readonly bit and reattempt the removal.
    This function is used by `shutil.rmtree` function.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)
