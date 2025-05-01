#!/bin/bash
set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Create and activate virtual environment if it doesn't exist
if [ ! -d "docs/venv" ]; then
    python3 -m venv docs/venv
fi
source docs/venv/bin/activate

# Install dependencies and package in development mode
pip install -r docs/requirements.txt
pip install -e .

# Create documentation directories
mkdir -p docs/source/_static
mkdir -p docs/build

# Generate documentation
cd docs
sphinx-build -b html source build

echo "Documentation built successfully in docs/build/index.html"
