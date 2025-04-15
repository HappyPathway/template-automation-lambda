####################################################################################
# This Lambda function takes JSON input, processes it using a Jinja2 template,
# and writes the output to a file in a cloned GitHub repository.
# The changes are then committed and pushed to the Census GitHub Enterprise Server,
# creating a new repository for the Census EKS CI/CD pipeline.
####################################################################################

import os
import stat
import subprocess
import shutil
import logging

import json
from jinja2 import Environment, FileSystemLoader

# pylint: disable=import-error
from github import Github, Auth, GithubException
from git import Repo

# pylint: enable=import-error

import boto3
from botocore.exceptions import ClientError


CENSUS_GITHUB_API = "https://github.e.it.census.gov/api/v3"
ORG_NAME = "SCT-Engineering"
SECRET_NAME = "/eks-cluster-deployment/github_token"

ORIG_REPO_NAME = "template-eks-cluster"

TEMPLATE_FILE_NAME = "eks.hcl.j2"
HCL_FILE_NAME = "eks.hcl"

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")  # Set to "ERROR" to reduce logging messages.


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
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"result": rendered}),
    }


def operate_github(new_repo_name, eks_settings, output_hcl):
    """Clone a GitHub repo, add an EKS parameter file rendered
    from a template and the input JSON dta, and push to a new repo.

    Args:
        new_repo_name (str): Name of the new GitHub repo.
        eks_settings (json): Input JSON data with all the EKS parameter values.
        output_hcl (str): Name of the EKS parameter file in HCL format.

    Returns:
        str: The rendered EKS parameter string.
    """

    # Get both the original repo and the new repo objects from GitHub.
    # If the new repo doesn't exist, create it in GitHub.
    token = github_token()
    org = github_org(CENSUS_GITHUB_API, ORG_NAME, token)
    repo_orig = get_repo(org, ORIG_REPO_NAME)
    repo_new = get_repo(org, new_repo_name, create=True)

    # In case the new repo already exists locally, delete it.
    if os.path.exists(f"/tmp/{new_repo_name}"):
        shutil.rmtree(
            f"/tmp/{new_repo_name}", ignore_errors=False, onerror=remove_readonly
        )

    # Since Census GitHub Enterprise server uses a private TLS certificate,
    # the certificate veriification must be disabled.
    # This Git command will save the setting into ".gitconfig" file locally in the $HOME directory.
    # Because the only writable place in Lambda fucntion is "/tmp",
    # The HOME environment must be set to there.
    # This is done using the "Environment" attribute in the "template.yaml" file.
    cmd = ["git", "config", "--global", "http.sslVerify", "false"]
    subprocess.run(cmd, check=False)

    # Clone the original repo.
    # Since the only writable directory is "/tmp", we store the cloned repo there.
    repo_url_with_token = f"https://{token}@{repo_orig.html_url.split('//')[1]}"
    cloned_repo = Repo.clone_from(repo_url_with_token, f"/tmp/{new_repo_name}")

    # Change the remote URL of the local staging repo to the URL of the new repo.
    repo_url_with_token = f"https://{token}@{repo_new.html_url.split('//')[1]}"
    origin = cloned_repo.remotes.origin
    origin.set_url(repo_url_with_token)

    # If the default branch of the original repo is "master", rename it to "main".
    branch_name = cloned_repo.head.ref.name
    if branch_name == "master":
        current_branch = cloned_repo.heads.master
        current_branch.rename("main", force=True)

    # Render the j2 template using the input data.
    rendered = render_j2_template(eks_settings, TEMPLATE_FILE_NAME)
    # Write the renderd data to a file in the local staging repository root directory
    with open(f"/tmp/{new_repo_name}/{output_hcl}", "w") as file:
        file.write(rendered)

    # Commit and push the changes.
    cloned_repo.index.add(output_hcl)
    commit_message = "Add the EKS parameter file by the Lambda function"
    cloned_repo.index.commit(commit_message)
    cloned_repo.git.push("--set-upstream", origin.name, "main", force=True)

    return rendered


def get_repo(org, repo_name, create=False):
    """Retrieve a repository from GitHub Org.

    Args:
        org (obj): GitHub Organization object
        repo_name (str): Name of the repository to retrieve
        create (bool): Whether to create it if the named repository doesn't exist

    Returns:
        obj: GitHub repository object
    """
    try:
        repo = org.get_repo(repo_name)
    except GithubException as e:
        if e.status == 404:
            if create:
                logger.info("Create repo: %s", repo_name)
                repo_desc = "EKS Automation CI/CD Pipeline Repo"
                repo = org.create_repo(
                    repo_name,
                    description=repo_desc,
                    visibility="internal",
                    private=True,
                )
            else:
                logger.error("Repo: %s doesn't exist", repo_name)
                raise

    return repo


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


def github_org(base_url, org_name, token):
    """Get GitHub Organization Object

    Args:
        base_url (str): Base URL of the GitHub Org.
        org_name (str): name of the GitHub Org.
        token (str): Access token to authenticated to the GitHub Org.

    Returns:
        obj: the GitHub Org.
    """

    auth = Auth.Token(token)
    # Since Census GitHub Enterprise server uses a private TLS certificate,
    # the certificate veriification must be disabled.
    g = Github(auth=auth, base_url=base_url, verify=False)

    return g.get_organization(org_name)


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
        logger.error("Error occured when retrieving GitHub token from SSM Parameter")
        raise

    return token


def remove_readonly(func, path, _):
    """
    Clear the readonly bit and reattempt the removal.
    This function is used by `shutil.rmtree` function.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)
