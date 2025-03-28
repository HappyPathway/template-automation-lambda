##################################################################
# Script
# @usage python main.py
##################################################################
# import os
import sys
import json
from loguru import logger
from jinja2 import Environment, FileSystemLoader
from github import Github, Auth

# import boto3
from botocore.exceptions import ClientError
from .client.client import BotoClient

# import pygit2

CENSUS_GITHUB_API = "https://github.e.it.census.gov/api/v3"
REGION_NAME = "us-gov-east-1"
PROFILE = "224384469011-lab-gov-dev-nonprod"
ORG_NAME = "SCT-Engineering"


def get_github_token():

    bc = BotoClient(PROFILE, REGION_NAME, "secretsmanager")

    if bc is None:
        logger.critical("error connecting to AWS")
        logger.critical("exiting...bye")
        sys.exit()

    client = bc.create_client()

    secret_name = "dev/eks_automation_github_token"

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e

    secret = get_secret_value_response["SecretString"]

    return secret


def operate_github():

    token = get_github_token()

    auth = Auth.Token(token)
    g = Github(auth=auth, base_url=CENSUS_GITHUB_API)
    user = g.get_user()
    print(user.login)

    # print(g)
    # org = g.get_organization(ORG_NAME)

    # repo = org.get_repo("platform-tg-infra")
    # print(repo)

    # #create the new repository
    # repo = org.create_repo(projectName, description = projectDescription )

    # #create some new files in the repo
    # repo.create_file("/README.md", "init commit", readmeText)

    # #Clone the newly created repo
    # repoClone = pygit2.clone_repository(repo.git_url, '/path/to/clone/to')

    # #put the files in the repository here

    # #Commit it
    # repoClone.remotes.set_url("origin", repo.clone_url)
    # index = repoClone.index
    # index.add_all()
    # index.write()
    # author = pygit2.Signature("your name", "your email")
    # commiter = pygit2.Signature("your name", "your email")
    # tree = index.write_tree()
    # oid = repoClone.create_commit(
    #     'refs/heads/master',
    #     author,
    #     commiter,
    #     "init commit",
    #     tree,
    #     [repoClone.head.get_object().hex]
    #     )
    # remote = repoClone.remotes["origin"]
    # credentials = pygit2.UserPass(userName, password)
    # remote.credentials = credentials

    # callbacks=pygit2.RemoteCallbacks(credentials=credentials)

    # remote.push(['refs/heads/master'],callbacks=callbacks)


def main():
    """
    main entry routine
    """
    # Open and read the JSON file
    data = ""
    with open("data.json", "r") as file:
        data = json.load(file)

    jinja_env = Environment(loader=FileSystemLoader("templates/"), trim_blocks=True)
    template = jinja_env.get_template("eks.hcl.j2")
    rendered = template.render(data=data)

    print(rendered)

    # with open(template_location, "w") as file_obj:
    #     file_obj.write(rendered)

    logger.info("EKS CI/CD pipeline payload has been created!")

    operate_github()

    return True


if __name__ == "__main__":
    main()
