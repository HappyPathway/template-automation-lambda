"""
Lambda function entrypoint that imports the handler from the template_automation package.

This file resolves the 'attempted relative import with no known parent package'
error by placing an entrypoint at the root level of the Lambda package.
"""

import sys
import os
import importlib.util

# Add Lambda task root directory to Python path
sys.path.insert(0, '/var/task')

# Try to read environment variables if they exist
if os.path.exists('/var/task/.env'):
    with open('/var/task/.env', 'r') as env_file:
        for line in env_file:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
                if key == 'PYTHONPATH':
                    for path in value.split(':'):
                        if path and path not in sys.path:
                            sys.path.insert(0, path)

# Fallback check for critical dependencies
for module in ['pydantic', 'jinja2']:
    try:
        importlib.import_module(module)
    except ImportError:
        print(f"Warning: {module} not found in standard paths. Looking in /var/task...")
        # Look for the module in /var/task
        module_paths = [
            f'/var/task/{module}',
            f'/var/task/lib/python3.11/site-packages/{module}'
        ]
        for path in module_paths:
            if os.path.exists(path):
                sys.path.insert(0, os.path.dirname(path))
                break

from template_automation.app import lambda_handler

# Re-export the lambda_handler function for Lambda runtime to find it
__all__ = ['lambda_handler']
