# -*- coding: utf8 -*-

"""MongoDB GridFS adapter for Pjuu

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""
from pymongo import MongoClient, uri_parser
import gridfs


class GridFS:
    def __init__(self, config, client=None):
        if client is None:
            parsed_uri = uri_parser.parse_uri(
                config.get('STORE_GRIDFS_MONGO_URI'))
            database_name = parsed_uri['database']

            self.cx = MongoClient(config.get('STORE_GRIDFS_MONGO_URI'))

            if database_name:
                self.db = self.cx[database_name]
            else:
                self.db = self.cx.db  # No real fall back
        else:
            self.db = client

        self.grid = gridfs.GridFS(
            self.db, collection=config.get('STORE_GRIDFS_COLLECTION'))

    def get(self, filename):
        return self.grid.get_version(filename=filename)

    def put(self, file, filename, content_type):
        self.grid.put(file, filename=filename, content_type=content_type)

    def delete(self, filename):
        cursor = self.grid.find({'filename': filename})
        for f in cursor:
            return self.grid.delete(f._id)

    def exists(self, filename):
        return self.grid.exists(filename=filename)
