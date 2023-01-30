# -*- coding: utf8 -*-

"""Different storage backends available for Pjuu

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2023 Joe Doherty

"""

from flask import url_for
from .filesystem import Filesystem
from .s3 import S3
from .gridfs import GridFS


class InvalidStorageBackend(Exception):
    pass


class Storage:
    """Manage files in side pjuu

    :param app: Flask instance
    """

    def __init__(self, app=None):
        self.app = app

    def init_app(self, app, *args, **kwargs):
        self.app = app
        self.backend = app.config.get('STORE_BACKEND', None).lower()
        self.cdn_url = app.config.get('STORE_CDN_URL', '')
        self.cdn = True if self.cdn_url.strip() != '' else False

        # Inject storage_url_for in to apps template environment
        app.jinja_env.globals.update(storage_url_for=self.url_for)

        if self.backend == 'file':
            self.store = Filesystem(app.config, *args, **kwargs)
        elif self.backend == 'gridfs':
            self.store = GridFS(app.config, *args, **kwargs)
        elif self.backend == 's3':
            self.store = S3(app.config, *args, **kwargs)
        else:
            raise InvalidStorageBackend

    def get(self, filename):
        return self.store.get(filename)

    def put(self, file, filename, content_type):
        return self.store.put(file, filename, content_type)

    def delete(self, filename):
        return self.store.delete(filename)

    def exists(self, filename):
        return self.store.exists(filename)

    def url_for(self, endpoint, **values):
        """Wraps Flask.url_for, if CDN is enabled will use that else will
        send user to correct url
        """
        if self.cdn:
            return '{0}/{1}'.format(
                self.cdn_url, values.get('filename'))  # pragma: nocover
        else:
            return url_for(endpoint, **values)
