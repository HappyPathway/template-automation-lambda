#!/usr/bin/env python3
"""
Setup script for Lambda container image
Handles installation of dependencies and verification of Lambda environment
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Constants
LAMBDA_TASK_ROOT = '/var/task'
TMP_DIR = '/tmp'

def run_command(cmd, check=True):
    """Run a shell command and print its output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, check=check,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout)
    return result

def copy_directory(src, dest):
    """Copy a directory to destination"""
    print(f"Copying '{src}' to '{dest}'")
    shutil.copytree(src, dest, dirs_exist_ok=True)

def copy_file(src, dest):
    """Copy a file to destination"""
    print(f"Copying '{src}' to '{dest}'")
    shutil.copy2(src, dest)

def install_dependencies():
    """Install Python dependencies"""
    print("=== Installing dependencies from requirements.txt ===")
    run_command(f"pip3 install --no-cache-dir -r {TMP_DIR}/requirements.txt -t {LAMBDA_TASK_ROOT} -v")
    
    # Explicitly install pydantic to ensure it's available
    print("=== Explicitly installing pydantic ===")
    run_command(f"pip3 install --no-cache-dir pydantic -t {LAMBDA_TASK_ROOT} -v")
    
    print("=== Installing package in development mode ===")
    run_command(f"pip3 install --no-cache-dir -e {TMP_DIR} -t {LAMBDA_TASK_ROOT} -v")

def verify_dependencies():
    """Verify that key dependencies are installed correctly"""
    print("=== Verifying dependencies installation ===")
    
    # Print Python path for debugging
    print("Python sys.path:")
    run_command("python3 -c 'import sys; print(sys.path)'")
    
    # Check key dependencies
    dependencies = [
        "jinja2", 
        "github",    # PyGithub
        "pydantic", 
        "boto3",
        "template_automation"
    ]
    
    for dep in dependencies:
        cmd = f"python3 -c 'import {dep}; print(f\"{dep} installed successfully\")'  || echo '{dep} not installed correctly'"
        run_command(cmd, check=False)

def setup_lambda_environment():
    """Main function to set up the Lambda environment"""
    print("=== Setting up Lambda environment ===")
    
    # Debug info
    print("=== Python and pip versions ===")
    run_command("python3 --version")
    run_command("pip3 --version")
    
    # Install dependencies
    install_dependencies()
    
    # Copy app.py to Lambda task root
    print("=== Copying app.py to Lambda task root ===")
    copy_file(f"{TMP_DIR}/app.py", f"{LAMBDA_TASK_ROOT}/app.py")
    
    # Copy template_automation directory
    print("=== Copying template_automation package ===")
    copy_directory(f"{TMP_DIR}/template_automation", f"{LAMBDA_TASK_ROOT}/template_automation")
    
    # Verify dependencies
    verify_dependencies()
    
    # List installed packages
    print("=== Listing installed Python packages ===")
    run_command("pip3 list")
    
    # Verify task directory structure
    print("=== Verifying Lambda task root contents ===")
    run_command(f"ls -la {LAMBDA_TASK_ROOT}")
    run_command(f"ls -la {LAMBDA_TASK_ROOT}/template_automation")

if __name__ == "__main__":
    setup_lambda_environment()
    print("Lambda setup completed successfully")
    sys.exit(0)