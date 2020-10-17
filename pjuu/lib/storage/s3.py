# -*- coding: utf8 -*-

"""S3 adapter for Pjuu

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""
import io
from boto3 import session
from botocore.exceptions import ClientError


class S3:
    def __init__(self, config):
        self.bucket = config.get('STORE_S3_BUCKET')
        self.session = session.Session()
        self.client = self.session.client(
            's3',
            region_name=config.get('STORE_S3_REGION'),
            endpoint_url=config.get('STORE_S3_ENDPOINT'),
            aws_access_key_id=config.get('STORE_S3_ACCESS_KEY'),
            aws_secret_access_key=config.get('STORE_S3_SECRET_KEY')
        )

    def get(self, filename):
        data = self.client.get_object(Bucket=self.bucket, Key=filename)
        return io.BytesIO(data['Body'].read())

    def put(self, file, filename, content_type):
        self.client.put_object(
            Bucket=self.bucket,
            Key=filename,
            Body=file,
            ACL='public-read',
            ContentType=content_type
        )

    def delete(self, filename):
        self.client.delete_object(Bucket=self.bucket, Key=filename)

    def exists(self, filename):
        try:
            self.client.head_object(Bucket=self.bucket, Key=filename)
            return True
        except ClientError:
            return False
