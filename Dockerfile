FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first to leverage Docker cache
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -t ${LAMBDA_TASK_ROOT}

# Copy the template_automation package
COPY template_automation/ ${LAMBDA_TASK_ROOT}/template_automation/

# Copy the root app.py file (this is essential for AWS Lambda to find the handler)
COPY app.py ${LAMBDA_TASK_ROOT}/

# Ensure the Lambda handler is correctly set
CMD [ "app.lambda_handler" ]
