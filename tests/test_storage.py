# -*- coding: utf8 -*-

"""Tests for uploading of files in to MongoDB GridFS.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2023 Joe Doherty

"""
import io
from pathlib import Path
import unittest
from flask import Flask
from pjuu.configurator import load as load_config
from pjuu.lib import get_uuid
from pjuu.lib.storage import Storage, InvalidStorageBackend


class StorageTests(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        config = load_config()
        self.app.config.update(config)

    def test_file(self):
        self.app.config.update(
            STORE_BACKEND='file',
            STORE_FILE_DIR='/tmp'
        )
        storage = Storage()
        storage.init_app(self.app)

        filename = '{0}.txt'.format(get_uuid())
        test_text = b'Hello world'

        self.assertEqual(storage.backend, 'file')
        self.assertEqual(storage.store.dir, Path('/tmp'))
        self.assertFalse(storage.exists(filename))

        storage.put(io.BytesIO(test_text), filename, 'text/plain')
        self.assertTrue(storage.exists(filename))

        data = storage.get(filename)
        self.assertEqual(data.read(), io.BytesIO(test_text).read())

        storage.delete(filename)
        self.assertFalse(storage.exists(filename))

        # Ensure no error is thrown if you delete a file that doesn't exist
        storage.delete(filename)

    def test_gridfs(self):
        self.app.config.update(
            STORE_BACKEND='gridfs',
            STORE_GRIDFS_MONGO_URI='mongodb://localhost:27017/pjuu',
            STORE_GRIDFS_COLLECTION='testing'
        )
        storage = Storage()
        storage.init_app(self.app)

        filename = '{0}.txt'.format(get_uuid())
        test_text = b'Hello world'

        self.assertEqual(storage.backend, 'gridfs')
        self.assertEqual(storage.store.uri, 'mongodb://localhost:27017/pjuu')
        self.assertEqual(storage.store.collection, 'testing')
        self.assertFalse(storage.exists(filename))

        storage.put(io.BytesIO(test_text), filename, 'text/plain')
        self.assertTrue(storage.exists(filename))

        data = storage.get(filename)
        self.assertEqual(data.read(), io.BytesIO(test_text).read())

        storage.delete(filename)
        self.assertFalse(storage.exists(filename))

        # Ensure no error is thrown if you delete a file that doesn't exist
        storage.delete(filename)

    def test_s3(self):
        self.app.config.update(
            STORE_BACKEND='s3',
            # Rest of config comes from environment
        )
        storage = Storage()
        storage.init_app(self.app)

        filename = '{0}.txt'.format(get_uuid())
        test_text = b'Hello world'

        self.assertEqual(storage.backend, 's3')
        # As the S3 bucket is a real one used for testing I am not
        # going to check it's config
        self.assertFalse(storage.exists(filename))

        storage.put(io.BytesIO(test_text), filename, 'text/plain')
        self.assertTrue(storage.exists(filename))

        data = storage.get(filename)
        self.assertEqual(data.read(), io.BytesIO(test_text).read())

        storage.delete(filename)
        self.assertFalse(storage.exists(filename))

        # Ensure no error is thrown if you delete a file that doesn't exist
        storage.delete(filename)

    def test_invalid(self):
        self.app.config.update(
            STORE_BACKEND='invalid',
        )
        storage = Storage()
        self.assertRaises(InvalidStorageBackend,
                          lambda: storage.init_app(self.app))
