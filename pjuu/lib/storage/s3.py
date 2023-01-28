# -*- coding: utf8 -*-

"""S3 adapter for Pjuu

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2023 Joe Doherty

"""
import io
from boto3 import session
from botocore.exceptions import ClientError


class S3:
    def __init__(self, config):
        self.region = config.get('STORE_S3_REGION')
        self.endpoint = config.get('STORE_S3_ENDPOINT')
        self.access_key = config.get('STORE_S3_ACCESS_KEY')
        self.secret_key = config.get('STORE_S3_SECRET_KEY')
        self.bucket = config.get('STORE_S3_BUCKET')
        self.acl = config.get('STORE_S3_ACL')

        self.session = session.Session()
        self.client = self.session.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def get(self, filename):
        data = self.client.get_object(Bucket=self.bucket, Key=filename)
        return io.BytesIO(data['Body'].read())

    def put(self, file, filename, content_type):
        self.client.put_object(
            Bucket=self.bucket,
            Key=filename,
            Body=file,
            ACL=self.acl,
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
