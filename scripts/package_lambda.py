#!/usr/bin/env python3
"""
Lambda Function and Layer Packaging Script

This script packages AWS Lambda function code and its dependencies into separate
zip files ready for deployment. It handles both the main function code and
a Lambda layer containing Python dependencies.
"""

import asyncio
import logging
import os
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("lambda_packager")

@dataclass
class PackageConfig:
    """Configuration for Lambda packaging."""
    workspace_dir: Path
    dist_dir: Path
    lambda_dir: Path
    requirements_file: Path

    @classmethod
    def from_workspace(cls, workspace_dir: Path) -> "PackageConfig":
        """Create config from workspace directory."""
        return cls(
            workspace_dir=workspace_dir,
            dist_dir=workspace_dir / "dist",
            lambda_dir=workspace_dir / "eks_automation",
            requirements_file=workspace_dir / "eks_automation" / "requirements.txt"
        )

class PackagingError(Exception):
    """Base exception for packaging errors."""
    pass

class DirectoryManager:
    """Manages creation and cleanup of directories."""
    
    def __init__(self, directory: Path):
        self.directory = directory

    def __enter__(self) -> Path:
        """Create clean directory."""
        if self.directory.exists():
            shutil.rmtree(self.directory)
        self.directory.mkdir(parents=True)
        return self.directory

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle cleanup if needed."""
        if exc_type is not None:
            logger.error(f"Error occurred: {exc_val}")
            return False
        return True

def create_zip(source_dir: Path, output_file: Path) -> None:
    """Create a zip file from a directory."""
    logger.info(f"Creating zip file: {output_file}")
    if not source_dir.exists():
        raise PackagingError(f"Source directory does not exist: {source_dir}")
        
    if not any(source_dir.iterdir()):
        raise PackagingError(f"Source directory is empty: {source_dir}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    if output_file.exists():
        output_file.unlink()

    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                rel_dir = os.path.relpath(root, source_dir)
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(rel_dir, file)
                    if rel_dir == '.':
                        arcname = file
                    zf.write(file_path, arcname)
                    
        if not output_file.exists():
            raise PackagingError(f"Zip file was not created: {output_file}")
    except Exception as e:
        raise PackagingError(f"Failed to create zip file: {str(e)}")

async def create_constraints_file(target_dir: Path) -> Path:
    """Create a constraints file to ensure compatibility with Lambda runtime."""
    constraints_file = target_dir / "constraints.txt"
    
    logger.info("Creating constraints file for Lambda compatibility")
    with open(constraints_file, "w") as f:
        f.write("# Constraints for Lambda compatibility\n")
        f.write("# Pin cryptography to version compatible with Lambda's GLIBC\n")
        f.write("cryptography<38.0.0\n")
        f.write("# Additional constraints for Lambda compatibility\n")
        f.write("PyGithub<1.59.0\n")
        f.write("GitPython<3.1.31\n")
    
    return constraints_file

async def install_requirements(requirements_file: Path, target_dir: Path) -> None:
    """Install Python requirements to target directory with constraints."""
    # Create constraints file
    constraints_file = await create_constraints_file(target_dir.parent)
    
    logger.info(f"Installing requirements with constraints for Lambda compatibility")
    process = await asyncio.create_subprocess_exec(
        "pip", "install", "-r", str(requirements_file), "-t", str(target_dir),
        "--constraint", str(constraints_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise PackagingError(f"pip install failed: {stderr.decode()}")

async def package_lambda(config: PackageConfig) -> None:
    """Package Lambda function and layer."""
    try:
        # Set up directories
        logger.info("Setting up directories...")
        lambda_dist = config.dist_dir / "lambda"
        layer_dir = config.dist_dir / "layer"
        layer_python_dir = layer_dir / "python"

        # Create directories
        with DirectoryManager(lambda_dist):
            # Copy Lambda function code
            logger.info("Copying Lambda function code...")
            shutil.copytree(config.lambda_dir, lambda_dist, dirs_exist_ok=True)
            # Create function zip
            create_zip(lambda_dist, config.dist_dir / "eks_automation.zip")

        # Create layer if requirements exist
        if config.requirements_file.exists():
            with DirectoryManager(layer_python_dir):
                logger.info("Installing Python requirements...")
                await install_requirements(config.requirements_file, layer_python_dir)
                # Create zip from the layer directory containing the python subdirectory
                create_zip(layer_python_dir.parent, config.dist_dir / "layer.zip")
        else:
            raise PackagingError("requirements.txt not found")
    except Exception as e:
        logger.error(f"Packaging failed: {str(e)}")
        raise PackagingError(f"Lambda packaging failed: {str(e)}")

    logger.info("Successfully created Lambda package and layer")

def main() -> None:
    """Main entry point."""
    try:
        if len(sys.argv) != 2:
            raise PackagingError("Usage: package_lambda.py <workspace_dir>")

        workspace_dir = Path(sys.argv[1])
        if not workspace_dir.exists():
            raise PackagingError(f"Workspace directory not found: {workspace_dir}")

        config = PackageConfig.from_workspace(workspace_dir)
        asyncio.run(package_lambda(config))

    except PackagingError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()
