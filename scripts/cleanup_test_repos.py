# scripts/cleanup_test_repos.py
import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_env_var(name):
    """Get an environment variable or raise an error."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Environment variable {name} is not set.")
    return value

def delete_repository(api_base_url, headers, org_name, repo_name):
    """Delete a specific repository."""
    delete_url = f"{api_base_url}/repos/{org_name}/{repo_name}"
    try:
        response = requests.delete(
            delete_url,
            headers=headers,
            verify=False  # Consider adding proper verification
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        logging.info(f"Successfully deleted repository: {repo_name}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to delete repository {repo_name}: {e}")
        if e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            logging.error(f"Response text: {e.response.text}")
        else:
            logging.error("No response received from the API.")

def list_and_archive_test_repos(api_base_url, headers, org_name):
    """List all repositories in the org and delete those matching the pattern."""
    repos_url = f"{api_base_url}/orgs/{org_name}/repos"
    params = {'per_page': 100}  # Adjust per_page as needed
    page = 1
    deleted_count = 0

    logging.info(f"Fetching repositories from organization: {org_name}")

    while True:
        params['page'] = page
        logging.info(f"Fetching page {page} of repositories...")
        try:
            response = requests.get(repos_url, headers=headers, params=params, verify=False)
            response.raise_for_status()
            repos = response.json()
            logging.info(f"Found {len(repos)} repositories on page {page}.")

            if not repos:
                logging.info("No more repositories found.")
                break

            logging.info(f"Processing page {page} of repositories...")
            for repo in repos:
                repo_name = repo.get("name")
                is_archived = repo.get("archived", False)
                if repo_name and repo_name.startswith("temp-test-repo-"):
                    logging.info(f"Found test repository: {repo_name}")
                    logging.info(f"Deleting repository: {repo_name}")
                    delete_repository(api_base_url, headers, org_name, repo_name)
                    logging.info(f"Deleted repository: {repo_name}")
                    deleted_count += 1

            # Check if there's a next page (GitHub uses Link header)
            if 'next' not in response.links:
                break
            # Use the URL provided in the Link header for the next page
            # Need to update repos_url for the next iteration
            next_link = response.links.get('next')
            if next_link:
                repos_url = next_link['url']
                page += 1 # Increment page conceptually, actual page number is in the URL
            else:
                 break # No next link header means we are done

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch repositories: {e}")
            if e.response is not None:
                logging.error(f"Response status: {e.response.status_code}")
                logging.error(f"Response text: {e.response.text}")
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

    logging.info(f"Finished cleanup. Deleted {deleted_count} test repositories during this run.")

if __name__ == "__main__":
    try:
        token = get_env_var("GITHUB_TOKEN")
        api_url = get_env_var("GITHUB_API")
        org = get_env_var("GITHUB_ORG")

        req_headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

        # Suppress InsecureRequestWarning for verify=False
        # Ensure urllib3 is available or handle the import error
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            logging.warning("urllib3 not found, cannot disable InsecureRequestWarning.")

        list_and_archive_test_repos(api_url, req_headers, org)

    except ValueError as e:
        logging.error(e)
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred during script execution: {e}")
        exit(1)
