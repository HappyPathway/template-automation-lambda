"""
Boto client
TODO: change client to assume role
"""

import boto3
from botocore.exceptions import ClientError
from loguru import logger


class BotoClient:
    def __init__(self, profile, region, service):
        """
        BotoClient constructor
        """
        self.profile = profile
        self.region = region
        self.service = service

    def create_client(self):
        """
        creates a boto session and returns a client for a given profile
        """
        try:
            session = boto3.session.Session(profile_name=self.profile)
            client = session.client(service_name=self.service, region_name=self.region)

            return client

        except ClientError as error:
            logger.critical(f"error creating client {error}")
            return None
