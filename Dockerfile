# DEPRECATED: This Dockerfile is not used for deployment.
# Lambda container image is built using Packer (see packer.pkr.hcl)
# ----------------------------------------------------------------
# Keeping this file for reference only

FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first to leverage Docker cache
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -t /var/task

# Copy all code files for package installation
COPY . /tmp/app/

# Install the package in development mode to make it available to Python
RUN pip install -e /tmp/app -t /var/task

# Explicitly copy the template_automation package to the Lambda task root
COPY template_automation /var/task/template_automation/

# Copy the root app.py file (this is essential for AWS Lambda to find the handler)
COPY app.py /var/task/

# Ensure the Lambda handler is correctly set
CMD [ "app.lambda_handler" ]
