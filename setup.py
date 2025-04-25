from setuptools import setup, find_packages

setup(
    name="template-automation",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3",
        "requests"
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-mock"
        ]
    }
)
