#!/usr/bin/env python3
"""
Script to invoke the EKS Automation Lambda function via API Gateway.
Parses Terraform outputs to get the API Gateway URL, log group name, and AWS region.
"""

import json
import argparse
import subprocess
import sys
import requests
import os
import time
import boto3
import datetime


class LambdaInvoker:
    """Class for invoking Lambda functions and managing related operations."""
    
    def __init__(self):
        """Initialize the LambdaInvoker."""
        self.api_url = None
        self.log_group_name = None
        self.invocation_start_time = None
        self.aws_region = None
        self.session = None
    
    @staticmethod
    def get_terraform_output(output_name):
        """Get a specific Terraform output value by name."""
        try:
            # Run Terraform output command
            result = subprocess.run(
                f"tf output -raw {output_name}",
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            output_data = result.stdout
            return output_data
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving Terraform output '{output_name}': {e}")
            print(f"stderr: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing Terraform output as JSON: {e}")
            return None
    
    def initialize_from_terraform(self):
        """Initialize API URL and log group name from Terraform outputs."""
        # Get API Gateway URL from Terraform output
        output_name = "api_gateway_invoke_url"
        self.api_url = self.get_terraform_output(output_name)
        print(f"Found API Gateway URL in output: {output_name}. {self.api_url}")
        if not self.api_url:
            print("Error: Failed to find API Gateway URL in Terraform outputs")
            return False
        
        # Get log group name from Terraform output
        self.log_group_name = self.get_terraform_output("log_group")
        if not self.log_group_name:
            print("Warning: Failed to find CloudWatch log group in Terraform outputs")
            print("CloudWatch logs will not be available")
        else:
            print(f"CloudWatch log group: {self.log_group_name}")
        
        # Get AWS region from Terraform output
        self.aws_region = self.get_terraform_output("aws_region")
        if not self.aws_region:
            print("Warning: Failed to find AWS region in Terraform outputs")
            print("Attempting to use default AWS region from environment or config")
        else:
            print(f"AWS Region: {self.aws_region}")
            
        print(f"API Gateway URL: {self.api_url}")
        return True
        
    def initialize_aws_session(self, profile_name=None):
        """
        Initialize AWS session for accessing AWS services
        
        Priority order for credentials:
        1. AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
        2. AWS profile if specified
        3. Default credential provider chain
        
        Args:
            profile_name: Optional AWS profile name to use (lower priority than env vars)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if AWS environment variables are set
            if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
                print("Using AWS credentials from environment variables")
                # When using environment variables, boto3.Session() will automatically pick them up
                self.session = boto3.Session(region_name=self.aws_region)
            elif profile_name:
                print(f"Using AWS profile: {profile_name}")
                self.session = boto3.Session(profile_name=profile_name, region_name=self.aws_region)
            else:
                print("Using default AWS credentials")
                self.session = boto3.Session(region_name=self.aws_region)
                
            # Test that credentials are valid
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            print(f"Using AWS account: {identity['Account']}")
            print(f"Using IAM identity: {identity['Arn']}")
            return True
        except Exception as e:
            print(f"Error initializing AWS session: {e}")
            print("Make sure your AWS credentials are properly configured")
            print("Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and optionally AWS_SESSION_TOKEN environment variables")
            return False
    
    def prepare_payload(self, args):
        """Prepare the payload for Lambda invocation based on command-line arguments."""
        payload = None
        if args.input:
            try:
                with open(args.input, 'r') as f:
                    payload = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error reading input file: {e}")
                return None
        elif args.payload:
            try:
                payload = json.loads(args.payload)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON payload: {e}")
                return None
        else:
            # Default minimal payload if none provided
            payload = {"message": "Test invocation"}
        
        print(f"Sending payload: {json.dumps(payload, indent=2)}")
        return payload
        
    def invoke_lambda(self, payload, show_logs=False):
        """
        Invoke the Lambda function via API Gateway and handle response
        
        Args:
            payload: The payload to send to the Lambda function
            show_logs: Whether to show CloudWatch logs regardless of success
            
        Returns:
            0 for success, 1 for failure
        """
        # Record start time for log filtering
        self.invocation_start_time = int(time.time() * 1000)
        
        try:
            response = requests.post(self.api_url, json=payload)
            print(f"Status code: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                print(f"Response (raw): {response.text}")
                
            # Check if we need to display logs
            should_show_logs = show_logs or not (200 <= response.status_code < 300)
            print(f"Show logs: {should_show_logs}")
            print(f"Log group name: {self.log_group_name}")
            
            # Fetch and display CloudWatch logs if needed
            if should_show_logs and self.log_group_name:
                # Wait a moment for logs to be available
                time.sleep(2)
                print("Fetching CloudWatch logs to help diagnose the issue...")
                log_events = self.fetch_cloudwatch_logs(start_time=self.invocation_start_time)
                self.display_cloudwatch_logs(log_events)
                
            # Return success if status code is 2xx
            if 200 <= response.status_code < 300:
                return 0
            else:
                return 1
        except requests.RequestException as e:
            print(f"Error invoking Lambda function: {e}")
            
            # Try to fetch logs on error
            if self.log_group_name:
                print("Fetching CloudWatch logs to help diagnose the issue...")
                log_events = self.fetch_cloudwatch_logs(start_time=self.invocation_start_time)
                self.display_cloudwatch_logs(log_events)
                
            return 1
    
    def fetch_cloudwatch_logs(self, start_time=None, limit=20):
        """
        Fetch recent logs from CloudWatch log group
        
        Args:
            start_time: Start time for logs in Unix timestamp milliseconds
            limit: Maximum number of log events to return
        
        Returns:
            List of log events
        """
        if not self.log_group_name:
            return []
            
        if start_time is None:
            # Default to fetching logs from 5 minutes ago
            start_time = int((datetime.datetime.now() - 
                            datetime.timedelta(minutes=5)).timestamp() * 1000)
        
        try:
            # Use the session to create a logs client with proper credentials
            if self.session:
                logs_client = self.session.client('logs')
            else:
                # Fallback to default client without session (uses environment credentials)
                logs_client = boto3.client('logs', region_name=self.aws_region)
                
            response = logs_client.filter_log_events(
                logGroupName=self.log_group_name,
                startTime=start_time,
                limit=limit,
                interleaved=True,
            )
            return response.get('events', [])
        except Exception as e:
            print(f"Error fetching CloudWatch logs: {e}")
            print("This might be due to insufficient IAM permissions or invalid credentials")
            return []
    
    def display_cloudwatch_logs(self, log_events):
        """
        Format and display CloudWatch log events
        
        Args:
            log_events: List of CloudWatch log events
        """
        if not log_events:
            print("No recent CloudWatch logs found")
            return
        
        print("\n=== Recent CloudWatch Logs ===")
        for event in log_events:
            timestamp = datetime.datetime.fromtimestamp(
                event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            message = event['message'].rstrip()
            print(f"[{timestamp}] {message}")
        print("=============================\n")


def main():
    """Main function to parse arguments and invoke the Lambda function."""
    parser = argparse.ArgumentParser(
        description="Invoke EKS Automation Lambda function via API Gateway"
    )
    parser.add_argument(
        "-i", "--input", 
        help="Path to JSON file containing input payload",
        default=os.path.join(os.path.dirname(__file__), "test_payload.json"),
        required=False
    )
    parser.add_argument(
        "-p", "--payload", 
        help="JSON string payload to send to Lambda",
        required=False
    )
    parser.add_argument(
        "--show-logs",
        help="Always show CloudWatch logs, even on success",
        action="store_true"
    )
    parser.add_argument(
        "--profile",
        help="AWS profile name to use for credentials (environment variables take precedence if set)",
        default=None
    )
    
    # Add an epilog message explaining credential options
    parser.epilog = """
    AWS Authentication:
    - Environment variables (preferred): AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional)
    - AWS profile (if specified with --profile)
    - Default credential provider chain
    """
    args = parser.parse_args()
    
    # Initialize the Lambda invoker
    invoker = LambdaInvoker()
    
    # Initialize from Terraform outputs
    if not invoker.initialize_from_terraform():
        sys.exit(1)
    
    # Initialize AWS session with credentials
    if not invoker.initialize_aws_session(profile_name=args.profile):
        print("Warning: Failed to initialize AWS session. Some features may not work.")
    
    # Prepare the payload
    payload = invoker.prepare_payload(args)
    if payload is None:
        sys.exit(1)
    
    # Invoke the Lambda function
    exit_code = invoker.invoke_lambda(payload, show_logs=args.show_logs)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
