##################################################################
# Script
# @usage python main.py
##################################################################
from __future__ import print_function

import os
import stat
import subprocess
import shutil
import logging

# import requests

import json
from jinja2 import Environment, FileSystemLoader

# pragma pylint: disable=E0401
from github import Github, Auth, GithubException
from git import Repo

# pragma pylint: enable=E0401

import boto3
from botocore.exceptions import ClientError


CENSUS_GITHUB_API = "https://github.e.it.census.gov/api/v3"
ORG_NAME = "SCT-Engineering"
SECRET_NAME = "/dev/eks_automation_github_token"

TEMPLATE_REPO_NAME = "platform-tg-infra"
NEW_REPO_NAME = "eks-automation-lambda-test1"

# Initialize the logger
logger = logging.getLogger()
logger.setLevel("INFO")


# pylint: disable-next=W0613
def lambda_handler(event, context):

    # personId = event['queryStringParameters']['personId']
    operate_github()

    return {"statusCode": 200, "message": "Processed successfully"}


def operate_github():
    org, token = github_org(CENSUS_GITHUB_API, ORG_NAME)
    repo_template = template_repo(org, TEMPLATE_REPO_NAME)
    repo_new = new_repo(org, NEW_REPO_NAME)

    if os.path.exists(NEW_REPO_NAME):
        shutil.rmtree(NEW_REPO_NAME, ignore_errors=False, onerror=remove_readonly)

    cmd = ["git", "config", "--global", "http.sslVerify", "false"]
    subprocess.run(cmd, check=False)

    repo_url_with_token = f"https://{token}@{repo_template.html_url.split('//')[1]}"

    cloned_repo = Repo.clone_from(repo_url_with_token, f"/tmp/{NEW_REPO_NAME}")
    origin = cloned_repo.remotes.origin
    repo_url_with_token = f"https://{token}@{repo_new.html_url.split('//')[1]}"
    origin.set_url(repo_url_with_token, allow_unsafe_protocols=True)

    branch_name = cloned_repo.head.ref.name
    if branch_name == "master":
        current_branch = cloned_repo.heads.master
        current_branch.rename("main", force=True)

    process_eks_data("data.json", "eks.hcl", "eks.hcl.j2")

    # os.chdir(NEW_REPO_NAME)
    cloned_repo.index.add("eks.hcl")
    commit_message = "Add a new file"
    cloned_repo.index.commit(commit_message)
    cloned_repo.git.push("--set-upstream", origin.name, "main", force=True)

    return True


def template_repo(org, template_repo_name):
    try:
        repo_template = org.get_repo(template_repo_name)
    except GithubException as e:
        if e.status == 404:
            logger.error("Repo: %s doesn't exist", template_repo_name)
            raise

    return repo_template


def new_repo(org, repo_name):
    try:
        repo_new = org.get_repo(repo_name)
    except GithubException as e:
        if e.status == 404:
            logger.info("Create repo: %s", repo_name)
            repo_desc = "EKS Automation CI/CD Pipeline Repo"
            repo_new = org.create_repo(
                repo_name, description=repo_desc, visibility="internal", private=True
            )

    return repo_new


def process_eks_data(
    json_fname, hcl_fname, j2_template_fname, j2_template_dir="templates/"
):
    # Open and read the JSON file
    data = ""
    with open(json_fname, "r") as file:
        data = json.load(file)

    jinja_env = Environment(loader=FileSystemLoader(j2_template_dir), trim_blocks=True)
    template = jinja_env.get_template(j2_template_fname)
    rendered = template.render(data=data)

    with open(f"/tmp/{NEW_REPO_NAME}/{hcl_fname}", "w") as file_obj:
        file_obj.write(rendered)

    return True


def github_org(base_url, org_name):
    token = github_token()
    auth = Auth.Token(token)
    g = Github(auth=auth, base_url=base_url, verify=False)

    return g.get_organization(org_name), token


def github_token():

    # session = boto3.session.Session(profile_name=PROFILE)
    # ssm = session.client(service_name="ssm", region_name=REGION_NAME)
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
    Clear the readonly bit and reattempt the removal
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)
