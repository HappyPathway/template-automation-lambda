Template Automation Lambda Documentation
=====================================

Welcome to the Template Automation Lambda documentation. This system provides a flexible
template automation framework for creating and configuring repositories from templates.

Quick Start
----------

The Template Automation Lambda is an AWS Lambda function that automates the process of creating
repositories from templates. It handles:

- Repository creation from templates
- Template rendering with variable substitution
- Pull request creation with customizable settings
- Workflow automation triggers

Installation
-----------

To install the package and its dependencies:

.. code-block:: bash

   pip install -r requirements.txt
   pip install -e .

Usage
-----

Basic usage example:

.. code-block:: python

   from template_automation.app import lambda_handler
   
   event = {
       "project_name": "my-new-repo",
       "owning_team": "devops",
       "template_settings": {
           "variables": {
               "environment": "prod",
               "region": "us-west-2"
           }
       }
   }
   
   lambda_handler(event, {})

API Documentation
---------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules/github_client
   modules/template_manager
   modules/models
   modules/lambda_handler

Core Components
-------------

- :doc:`modules/github_client` - GitHub API interaction for repository and PR management
- :doc:`modules/template_manager` - Template rendering and configuration handling
- :doc:`modules/models` - Pydantic data models for input validation
- :doc:`modules/lambda_handler` - AWS Lambda function entry point

Configuration
------------

The system uses several configuration models:

- **GitHubConfig**: GitHub API and authentication settings
- **WorkflowConfig**: Template workflow configuration
- **PRConfig**: Pull request settings
- **TemplateInput**: Input parameters for template processing

Environment Variables
-------------------

Required environment variables:

- ``GITHUB_TOKEN``: GitHub Personal Access Token
- ``GITHUB_ORG``: GitHub Organization name
- ``TEMPLATE_REPO``: Template repository name

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
