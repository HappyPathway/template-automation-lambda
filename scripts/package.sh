#!/bin/bash

# Create temporary directories
mkdir -p dist/lambda
mkdir -p dist/layer

# Package Lambda function
cp -r eks_automation/* dist/lambda/
cd dist/lambda
zip -r ../eks_automation.zip .
cd ../..

# Package Lambda layer
mkdir -p dist/layer/python
pip install -r eks_automation/requirements.txt -t dist/layer/python
cd dist/layer
zip -r ../layer.zip .
cd ../..

# Move zip files to root
mv dist/*.zip .

# Cleanup
rm -rf dist
