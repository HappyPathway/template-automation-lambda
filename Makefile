.PHONY: init venv install-deps clean terraform-init terraform-plan terraform-apply package all

PYTHON=python3
PIP=pip3
TERRAFORM=terraform
VENV=.venv
VENV_BIN=$(VENV)/bin
VENV_PIP=$(VENV_BIN)/pip

# Set PIP_CONFIG_FILE to use custom pip.conf
export PIP_CONFIG_FILE=$(CURDIR)/scripts/pip.conf

all: venv install-deps package terraform-apply

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

package: venv
	source $(VENV_BIN)/activate && chmod +x scripts/package.sh && ./scripts/package.sh

terraform-init:
	$(TERRAFORM) init

terraform-plan: terraform-init
	$(TERRAFORM) plan

terraform-apply: terraform-init package
	$(TERRAFORM) apply -auto-approve

terraform-destroy:
	$(TERRAFORM) destroy -auto-approve
