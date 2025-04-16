.PHONY: init venv install-deps clean init plan apply destroy all invoke-lambda package-lambda

PYTHON=python3
PIP=pip3
TERRAFORM=tf
VENV=.venv
VENV_BIN=$(VENV)/bin
VENV_PIP=$(VENV_BIN)/pip

# Set PIP_CONFIG_FILE to use custom pip.conf
export PIP_CONFIG_FILE=$(CURDIR)/scripts/pip.conf

all: venv install-deps apply

venv:
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip setuptools wheel

install-deps: venv
	source $(VENV_BIN)/activate && $(VENV_PIP) install -r scripts/requirements.txt

clean:
	rm -rf dist/
	rm -f *.zip
	rm -rf __pycache__/
	rm -rf .terraform/
	rm -rf $(VENV)

init:
	$(TERRAFORM) init

plan: init
	$(TERRAFORM) plan

apply: init
	$(TERRAFORM) apply -auto-approve

destroy: init
	$(TERRAFORM) destroy -auto-approve

invoke-lambda:
	@echo "Invoking Lambda function via API Gateway..."
	@source $(VENV_BIN)/activate && $(PYTHON) scripts/invoke_lambda.py $(ARGS)
	@echo "For more options, run: make invoke-lambda ARGS='-h'"

package-lambda: venv install-deps
	@echo "Packaging Lambda function and dependencies..."
	@mkdir -p dist
	@source $(VENV_BIN)/activate && $(PYTHON) scripts/package_lambda.py $(CURDIR)
	@echo "Tainting S3 objects to ensure they are recreated on next apply..."
	-$(TERRAFORM) taint 'aws_s3_object.lambda_package'
	-$(TERRAFORM) taint 'aws_s3_object.lambda_layer'
	@echo "Lambda package created successfully in the dist/ directory"
