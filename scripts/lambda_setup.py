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
PYTHON_VERSION = "3.11"  # Match the Lambda container's Python version

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
    
    # Create a site-packages directory if it doesn't exist
    site_packages = f"{LAMBDA_TASK_ROOT}/lib/python{PYTHON_VERSION}/site-packages"
    os.makedirs(site_packages, exist_ok=True)
    
    # Install dependencies directly to the site-packages directory
    run_command(f"pip3 install --no-cache-dir -r {TMP_DIR}/requirements.txt -t {LAMBDA_TASK_ROOT}")
    
    # Explicitly install critical dependencies
    print("=== Explicitly installing critical dependencies ===")
    run_command(f"pip3 install --no-cache-dir pydantic jinja2 PyGithub -t {LAMBDA_TASK_ROOT}")
    
    # Create a .pth file to ensure the Lambda runtime can find the packages
    with open(f"{LAMBDA_TASK_ROOT}/lambda_path.pth", "w") as f:
        f.write(f"{LAMBDA_TASK_ROOT}\n")
    
    print("=== Installing package in development mode ===")
    run_command(f"pip3 install --no-cache-dir -e {TMP_DIR} -t {LAMBDA_TASK_ROOT} -v")

def verify_dependencies():
    """Verify that key dependencies are installed correctly"""
    print("=== Verifying dependencies installation ===")
    
    # Print Python path for debugging
    print("Python sys.path:")
    run_command("python3 -c 'import sys; print(sys.path)'")
    
    # Check key dependencies
    dependencies = ['pydantic', 'jinja2', 'github']  # Add critical dependencies here
    with open(f"{TMP_DIR}/requirements.txt") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = line.split("=")[0].split("<")[0].split(">")[0].split("~")[0].strip()
                if pkg and pkg not in dependencies:
                    dependencies.append(pkg)
   
    # Use the Lambda container's Python to verify imports
    for dep in dependencies:
        cmd = f"cd {LAMBDA_TASK_ROOT} && python3 -c 'import {dep}; print(f\"{dep} installed successfully\")' || echo '{dep} not installed correctly'"
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
    
    # Create a wrapper script that ensures the Python path is set correctly
    with open(f"{LAMBDA_TASK_ROOT}/.env", "w") as f:
        f.write(f"PYTHONPATH={LAMBDA_TASK_ROOT}:{LAMBDA_TASK_ROOT}/lib/python{PYTHON_VERSION}/site-packages\n")
    
    # Verify dependencies
    verify_dependencies()
    
    # List installed packages
    print("=== Listing installed Python packages ===")
    run_command("pip3 list")
    
    # Verify task directory structure
    print("=== Verifying Lambda task root contents ===")
    run_command(f"ls -la {LAMBDA_TASK_ROOT}")
    run_command(f"ls -la {LAMBDA_TASK_ROOT}/template_automation")
    
    # Final check - try to import critical modules from the Lambda environment
    print("=== Testing key imports from Lambda environment ===")
    test_import = """
import sys
print("Python Path:", sys.path)
try:
    import pydantic
    print("pydantic successfully imported:", pydantic.__file__)
except ImportError as e:
    print("Error importing pydantic:", str(e))
try:
    import jinja2
    print("jinja2 successfully imported:", jinja2.__file__)
except ImportError as e:
    print("Error importing jinja2:", str(e))
try:
    import github
    print("github successfully imported:", github.__file__)
except ImportError as e:
    print("Error importing github:", str(e))
"""
    with open(f"{LAMBDA_TASK_ROOT}/test_imports.py", "w") as f:
        f.write(test_import)
    run_command(f"cd {LAMBDA_TASK_ROOT} && python3 test_imports.py")

if __name__ == "__main__":
    setup_lambda_environment()
    print("Lambda setup completed successfully")
    sys.exit(0)