"""Models for template automation."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GitHubConfig(BaseModel):
    """Configuration settings for GitHub API interactions.
    
    This class defines the settings needed to interact with the GitHub API,
    including the API URL, authentication token, organization name, and template
    repository information.

    Attributes:
        api_base_url (str): The base URL for all GitHub API requests. For example,
            "https://api.github.com" for public GitHub.
        token (str): Personal access token for GitHub API authentication.
        org_name (str): Organization name where repositories will be created.
        template_repo_name (Optional[str]): Name of the template repository to use
            as a base. Default is None.
        source_version (Optional[str]): Git reference (branch, tag, commit) to use
            from the template repository. Default is None.
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
    """Configuration for GitHub Actions workflow files.
    
    This class defines the structure for configuring GitHub Actions workflow files,
    including the workflow name, template source and destination paths, and any 
    variables needed for template rendering.

    Attributes:
        name (str): Name of the workflow, used for identification and logging.
        template_path (str): Path to the workflow template file, relative to the
            template root directory.
        output_path (str): Destination path where the rendered workflow file should
            be written in the target repository.
        variables (Dict[str, Any]): Variables to use when rendering the workflow
            template with Jinja2. Keys are variable names and values can be any
            type that Jinja2 can handle. Defaults to an empty dict.

    Example:
        >>> workflow = WorkflowConfig(
        ...     name="CI/CD",
        ...     template_path="workflows/ci.yml.j2",
        ...     output_path=".github/workflows/ci.yml",
        ...     variables={
        ...         "runner": "ubuntu-latest",
        ...         "python_version": "3.9"
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
        ...     trigger_init_workflow=True
        ... )
    """
    project_name: str
    template_settings: Dict[str, Any]
    trigger_init_workflow: bool = False
    owning_team: Optional[str] = None

class TemplateConfig(BaseModel):
    """Configuration for template repository automation.
    
    This class defines the overall configuration for how a template repository
    should be processed, including pull request settings and workflow automations.

    Attributes:
        pr (PRConfig): Configuration settings for pull request creation, including
            templates for title and body, branch names, and PR metadata.
        workflows (List[WorkflowConfig]): List of workflow configurations that should be
            applied to repositories created from this template.

    Example:
        >>> config = TemplateConfig(
        ...     pr=PRConfig(
        ...         title_template="Initialize {{ repo_name }}",
        ...         reviewers=["team-lead"]
        ...     ),
        ...     workflows=[
        ...         WorkflowConfig(
        ...             template_path="workflows/ci.yml",
        ...             variables={"runner": "ubuntu-latest"}
        ...         )
        ...     ]
        ... )
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
