"""
Lambda function entrypoint that imports the handler from the template_automation package.

This file resolves the 'attempted relative import with no known parent package'
error by placing an entrypoint at the root level of the Lambda package.
"""

from template_automation.app import lambda_handler

# Re-export the lambda_handler function for Lambda runtime to find it
__all__ = ['lambda_handler']
