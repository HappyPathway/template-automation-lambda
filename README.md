# EKS Automation Lambda

## Description

This repository hosts `eks-automation-lambda` automation work at `Census`.

## Dependencies

- `Anaconda` or a `bare bone Python 3` - create a `Remedy ticket` to have it available in `software center`
- `virtualenv` - must be installed outside of the `requirements.txt` install
- requirements.txt
- pre-commit hook

## Install `virtualenv`

```sh
pip install virtualenv

# below is the output from a successful install
$ virtualenv --version
virtualenv 20.25.0 from C:\Users\{your username}\AppData\Local\anaconda3\Lib\site-packages\virtualenv\__init__.py
```

## Create and activate `virtual environment`

```sh
virtualenv .venv

# activate env (windows)
.venv/Scripts/activate.ps1  (PowerShell)
.venv/Scripts/activate.bat  (Command Prompt)

# activate env (linux)
source .venv/bin/activate

# install dependencies
pip3 install -r requirements.txt

# deactivate env
deactivate
```

### Install pre-commit

Run the command below to install `pre-commit hooks` listed in the `.pre-commit-config.yaml`.

```sh
pre-commit install
```

### Tidy Up (manual linting)

`Pre-commit` does this automatically. This script is used to `lint / format python resources manually`. Run `tidy.sh` to `lint` and `format` code. This project uses `pylint` and `black`. Below is an example output from a successful run of this script.

```sh
--------------------------------------------------------------------
Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)

reformatted main.py


All done! ✨ 🍰 ✨
1 files reformatted, 1 files left unchanged.
```
