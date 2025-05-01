"""Template management and configuration using Jinja2."""

import os
import json
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import ValidationError
from .models import WorkflowConfig, PRConfig, TemplateConfig

class TemplateManager:
    """Handles the management and rendering of templates for workflows and pull requests.

    This class provides utilities to load template configurations, render workflow files,
    and generate pull request details based on templates and user-defined variables.

    Attributes:
        env (Environment): The Jinja2 environment for rendering templates.
        template_repo_name (str): The name of the template repository.
        config (TemplateConfig): The loaded template configuration.
    """

    def __init__(self, template_root: Optional[str] = None, template_repo_name: Optional[str] = None):
        """Initialize the TemplateManager with optional template root and repository name.

        Args:
            template_root (str, optional): The root directory for templates. Defaults to the
                'templates' directory in the same location as this file.
            template_repo_name (str, optional): The name of the template repository.
        """
        if template_root is None:
            template_root = os.path.join(os.path.dirname(__file__), "templates")

        self.env = Environment(
            loader=FileSystemLoader(template_root),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template_repo_name = template_repo_name
        self.config = self._load_template_config()

    def _load_template_config(self) -> TemplateConfig:
        """Load the template configuration from a .template-config.json file.

        Returns:
            TemplateConfig: The loaded configuration with validation.
            
        Raises:
            ValidationError: If the configuration is invalid.
        """
        try:
            config_path = os.path.join(os.getcwd(), ".template-config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    template_config = json.load(f)
                    return TemplateConfig(**template_config)
            return TemplateConfig()  # Use defaults if no config file exists
        except ValidationError as e:
            print(f"Warning: Template config validation failed: {str(e)}")
            return TemplateConfig()  # Use defaults on validation error
        except Exception as e:
            print(f"Warning: Could not load template config: {str(e)}")
            return TemplateConfig()  # Use defaults on any other error

    def render_workflow(self, workflow: WorkflowConfig) -> str:
        """Render a GitHub Actions workflow template.

        Args:
            workflow (WorkflowConfig): The workflow configuration containing template details.

        Returns:
            str: The rendered workflow content as a string.
        """
        template = self.env.get_template(workflow.template_path)
        return template.render(**workflow.variables)

    def render_pr_details(self, repo_name: str, workflow_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate pull request details by rendering templates and configurations.

        Args:
            repo_name (str): The name of the repository being created.
            workflow_files (List[str], optional): A list of workflow files being added.

        Returns:
            Dict[str, Any]: A dictionary containing the rendered pull request details.
        """
        pr_config = self.config.pr
        variables = {
            "repo_name": repo_name,
            "template_repo": self.template_repo_name,
            "workflow_files": workflow_files
        }

        return {
            "title": self.env.from_string(pr_config.title_template).render(**variables),
            "body": self.env.from_string(pr_config.body_template).render(**variables),
            "base_branch": pr_config.base_branch,
            "branch_name": f"{pr_config.branch_prefix}-{repo_name}",
            "labels": pr_config.labels,
            "reviewers": pr_config.reviewers,
            "assignees": pr_config.assignees
        }

    def get_workflow_configs(self) -> List[WorkflowConfig]:
        """Retrieve workflow configurations from the template configuration.

        Returns:
            List[WorkflowConfig]: A list of workflow configurations.
        """
        return self.config.workflows
