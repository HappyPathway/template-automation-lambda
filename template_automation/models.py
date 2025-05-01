"""Models for template automation."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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

    This class represents a single GitHub Actions workflow configuration,
    including its template source and destination paths, along with any
    variables needed for template rendering.

    Attributes:
        name (str): Descriptive name of the workflow, used for logging and
            identification purposes.
        template_path (str): Path to the Jinja2 template file containing the
            workflow definition. This path should be relative to the template
            root directory.
        output_path (str): Destination path where the rendered workflow file
            will be saved in the new repository. This path should be relative
            to the repository root.
        variables (Dict[str, Any]): Dictionary of variables to use when
            rendering the workflow template. These values will be passed to
            the Jinja2 template engine.

    Example:
        >>> workflow = WorkflowConfig(
        ...     name="CI/CD Pipeline",
        ...     template_path="workflows/ci.yml.j2",
        ...     output_path=".github/workflows/ci.yml",
        ...     variables={
        ...         "python_version": "3.9",
        ...         "test_commands": ["pytest", "flake8"]
        ...     }
        ... )
    """
    name: str
    template_path: str
    output_path: str
    variables: Dict[str, Any] = Field(default_factory=dict)

class PRConfig(BaseModel):
    """Specifies the configuration for creating pull requests.

    This class defines the structure and default values for pull request creation,
    including templates for title and body, branch configuration, and PR metadata
    like labels and reviewers.

    Attributes:
        title_template (str): Jinja2 template for the pull request title. Variables
            available include: repo_name, template_repo.
        body_template (str): Jinja2 template for the pull request body. Variables
            available include: repo_name, template_repo, workflow_files.
        base_branch (str): The target branch for the pull request. Defaults to "main".
        branch_prefix (str): Prefix for the feature branch name. The final branch name
            will be {prefix}-{repo_name}.
        labels (List[str]): Labels to automatically apply to the pull request.
            Defaults to ["automated"].
        reviewers (List[str]): GitHub usernames of reviewers to assign.
        assignees (List[str]): GitHub usernames of users to assign to the PR.

    Example:
        >>> pr_config = PRConfig(
        ...     title_template="Initialize {{ repo_name }} from template",
        ...     labels=["infrastructure", "automated"],
        ...     reviewers=["alice", "bob"]
        ... )
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

    This class defines the structure of input data needed to create a new
    repository from a template. It includes project metadata, template-specific
    settings, and optional configurations for repository ownership and
    initialization.

    Attributes:
        project_name (str): Name of the project/repository to create. This will
            be used as the repository name and in various template substitutions.
        template_settings (Dict[str, Any]): Dictionary of template-specific
            settings that will be written to the configuration file in the new
            repository. The structure depends on the template being used.
        trigger_init_workflow (bool): Whether to automatically trigger the
            initialization workflow after repository creation. Defaults to False.
        owning_team (Optional[str]): The GitHub team slug that should be granted
            admin access to the new repository. If None, no team access will be
            configured.

    Example:
        >>> input_data = TemplateInput(
        ...     project_name="my-new-service",
        ...     template_settings={
        ...         "environment": "production",
        ...         "region": "us-west-2"
        ...     },
        ...     trigger_init_workflow=True,
        ...     owning_team="platform-team"
        ... )
    """
    project_name: str
    template_settings: Dict[str, Any]
    trigger_init_workflow: bool = False
    owning_team: Optional[str] = None

class TemplateConfig(BaseModel):
    """Configuration for a template repository.
    
    This class defines the configuration structure for template repositories,
    including pull request settings and workflow configurations.

    Attributes:
        pr (PRConfig): Pull request configuration settings including title template,
            body template, branch settings, labels, reviewers and assignees.
        workflows (List[WorkflowConfig]): List of workflow configurations to apply
            to the repository. Each workflow config specifies name, template path,
            output path and variables.

    Example:
        ```python
        config = TemplateConfig(
            pr=PRConfig(
                title_template="Initialize {{ repo_name }}",
                base_branch="main",
                labels=["automated"]
            ),
            workflows=[
                WorkflowConfig(
                    name="CI",
                    template_path="workflows/ci.yml",
                    output_path=".github/workflows/ci.yml"
                )
            ]
        )
        ```
    """
    pr: PRConfig = Field(
        default_factory=lambda: PRConfig(
            title_template="Initialize {{ repo_name }} from template",
            body_template="""
            Automated pull request for initializing {{ repo_name }} from template {{ template_repo }}.
            
            This PR was created by the Template Automation system.
            {% if workflow_files %}
            ## Added Workflows
            {% for workflow in workflow_files %}
            - {{ workflow }}
            {% endfor %}
            {% endif %}
            """,
            base_branch="main",
            branch_prefix="init",
            labels=["automated"],
            reviewers=[],
            assignees=[]
        )
    )
    workflows: List[WorkflowConfig] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration.
        
        This inner class defines metadata for the TemplateConfig model,
        including example configurations and schema information.
        """
        json_schema_extra = {
            "example": {
                "pr": {
                    "title_template": "Initialize {{ repo_name }} from template",
                    "body_template": "Template PR body...",
                    "base_branch": "main",
                    "branch_prefix": "init",
                    "labels": ["automated"],
                    "reviewers": [],
                    "assignees": []
                },
                "workflows": []
            }
        }
