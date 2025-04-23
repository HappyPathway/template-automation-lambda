import os
import logging
import requests
import json

logger = logging.getLogger(__name__)

class GitHubClient:
    def trigger_workflow(self, repo_name, workflow_id="init-repo.yml", ref="main", inputs=None):
        """Trigger a GitHub Actions workflow in the repository
        
        Args:
            repo_name (str): Name of the repository
            workflow_id (str): The ID or filename of the workflow to trigger (default: init-repo.yml)
            ref (str): The git reference to run the workflow on (default: main)
            inputs (dict, optional): Input parameters for the workflow
            
        Returns:
            dict: Response from the workflow dispatch API
        """
        api_url = f"{self.api_base_url}/repos/{self.org_name}/{repo_name}/actions/workflows/{workflow_id}/dispatches"
        
        data = {
            "ref": ref,
        }
        if inputs:
            data["inputs"] = inputs
            
        response = requests.post(api_url, headers=self.headers, json=data, verify=False)
        
        if response.status_code == 204:  # GitHub returns 204 No Content for successful workflow dispatch
            logger.info(f"Successfully triggered workflow {workflow_id} in {repo_name}")
            return {"status": "success"}
        else:
            error_message = f"Failed to trigger workflow {workflow_id} in {repo_name}: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)

def operate_github(new_repo_name, template_settings, trigger_init_workflow=False):
    """Create and configure a new repository from template using GitHub API

    Args:
        new_repo_name (str): Name of the new GitHub repo
        template_settings (json): Input JSON data with all the template configuration values
        trigger_init_workflow (bool): Whether to trigger the init-repo workflow after setup

    Returns:
        None
    """
    # ... existing code ...

    logger.info(f"Successfully updated {new_repo_name} repository")

    if trigger_init_workflow:
        try:
            github.trigger_workflow(new_repo_name)
            logger.info("Successfully triggered init-repo workflow")
        except Exception as e:
            logger.warning(f"Failed to trigger init-repo workflow: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler to process incoming events and trigger GitHub operations

    Args:
        event (dict): The event data passed to the Lambda function
        context (object): The context object containing information about the invocation, function, and execution environment

    Returns:
        dict: Response object containing the status code and body
    """
    input_data = event.get("body")
    if isinstance(input_data, str):
        input_data = json.loads(input_data)

    project_name = input_data.get("project_name")
    template_settings = input_data.get("template_settings")
    trigger_init_workflow = input_data.get("trigger_init_workflow", False)
    
    logger.info(f"Project name: {project_name}")
    logger.info(f"Template settings to be applied: {json.dumps(template_settings, indent=2)}")
    logger.info(f"Trigger init workflow: {trigger_init_workflow}")

    if not project_name:
        logger.error("Missing project name in input")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing project name"})
        }

    try:
        logger.info(f"Starting GitHub operations for project: {project_name}")
        operate_github(project_name, template_settings, trigger_init_workflow)
        logger.info("GitHub operations completed successfully")
    except Exception as e:
        logger.error(f"Error during GitHub operations: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Operation completed successfully"})
    }