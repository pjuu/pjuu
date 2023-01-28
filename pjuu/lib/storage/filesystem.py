# -*- coding: utf8 -*-

"""Filesystem adapter for Pjuu

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2023 Joe Doherty

"""
import io
import os
from pathlib import Path


class Filesystem:
    def __init__(self, config):
        self.dir = Path(config.get('STORE_FILE_DIR', '/tmp'))

    def get(self, filename):
        f = open(self.dir.joinpath(filename), 'rb')
        data = io.BytesIO(f.read())
        f.close()
        # We can't store the data type along with the file so
        # we will have to guess
        return data

    def put(self, file, filename, content_type):
        f = open(self.dir.joinpath(filename), 'wb')
        f.write(file.read())
        f.close()

    def delete(self, filename):
        try:
            os.remove(self.dir.joinpath(filename))
        except FileNotFoundError:
            pass

    def exists(self, filename):
        return self.dir.joinpath(filename).is_file()
