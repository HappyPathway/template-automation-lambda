"""Models for template automation using Pydantic."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class GitHubConfig(BaseModel):
    """Encapsulates configuration settings for interacting with the GitHub API.

    Attributes:
        api_base_url (str): The base URL for GitHub API requests.
        token (str): The authentication token for GitHub.
        org_name (str): The name of the GitHub organization.
        commit_author_name (str): The name to use for commit authorship.
        commit_author_email (str): The email to use for commit authorship.
        source_version (Optional[str]): The version, tag, or SHA of the template to use.
        template_repo_name (Optional[str]): The name of the template repository.
        config_file_name (str): The name of the configuration file to write.
    """
    api_base_url: str
    token: str
    org_name: str
    commit_author_name: str = "Template Automation"
    commit_author_email: str = "automation@example.com"
    source_version: Optional[str] = None
    template_repo_name: Optional[str] = None
    config_file_name: str = "config.json"

class WorkflowConfig(BaseModel):
    """Defines the configuration for a GitHub Actions workflow.

    Attributes:
        name (str): The name of the workflow.
        template_path (str): The path to the workflow template file.
        output_path (str): The path where the rendered workflow file will be saved.
        variables (Dict[str, Any]): A dictionary of variables to substitute in the template.
    """
    name: str
    template_path: str
    output_path: str
    variables: Dict[str, Any] = Field(default_factory=dict)

class PRConfig(BaseModel):
    """Specifies the configuration for creating pull requests.

    Attributes:
        title_template (str): The template for the pull request title.
        body_template (str): The template for the pull request body.
        base_branch (str): The base branch for the pull request.
        branch_prefix (str): The prefix for the branch name.
        labels (List[str]): A list of labels to apply to the pull request.
        reviewers (List[str]): A list of reviewers to request for the pull request.
        assignees (List[str]): A list of assignees for the pull request.
    """
    title_template: str = "Initialize {{ repo_name }} from template"
    body_template: str = """
    Automated pull request for initializing {{ repo_name }} from template {{ template_repo }}.
    
    This PR was created by the Template Automation system.
    
    ## Changes
    - Initial repository setup from template
    - Configuration files added
    {% if workflow_files %}
    - Added workflow files:
      {% for workflow in workflow_files %}
      - {{ workflow }}
      {% endfor %}
    {% endif %}
    """
    base_branch: str = "main"
    branch_prefix: str = "init"
    labels: List[str] = Field(default_factory=lambda: ["automated"])
    reviewers: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)

class TemplateInput(BaseModel):
    """Represents the input data required for template automation.

    Attributes:
        project_name (str): The name of the project to create.
        template_settings (Dict[str, Any]): A dictionary of settings for the template.
        trigger_init_workflow (bool): Whether to trigger the initialization workflow.
        owning_team (Optional[str]): The name of the team that will own the repository.
    """
    project_name: str
    template_settings: Dict[str, Any]
    trigger_init_workflow: bool = False
    owning_team: Optional[str] = None
