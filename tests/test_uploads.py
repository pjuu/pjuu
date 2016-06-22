# -*- coding: utf8 -*-

"""Tests for uploading of files in to MongoDB GridFS.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import gridfs
import io
from os import listdir
from os.path import isfile, join, splitext

from pjuu import mongo as m
from pjuu.lib.uploads import process_upload, get_upload, delete_upload

from tests import FrontendTestCase


class PagesTests(FrontendTestCase):

    def test_uploads(self):
        """Simply tests the backend functions in `lib.uploads`.

        Also tests `posts.get_upload` since this is only a simple wrapper
        around the backend function.

        """
        test_upload_dir = 'tests/upload_test_files/'
        test_upload_files = [
            join(test_upload_dir, f) for f in listdir(test_upload_dir)
            if isfile(join(test_upload_dir, f))
        ]

        # Create a GridFS object to test image deletion
        grid = gridfs.GridFS(m.db, collection='uploads')

        # Test each file in the upload directory
        for f in test_upload_files:
            image = io.BytesIO(
                open(f).read()
            )
            filename = process_upload(image)

            # Get the upload these are designed for being served directly by
            # Flask. This is a Flask/Werkzeug response object
            image = get_upload(filename)
            self.assertTrue(grid.exists({'filename': filename}))

            _, file_extension = splitext(f)
            if file_extension.lower() == '.gif':
                file_type = 'image/gif'
            else:
                file_type = 'image/png'

            self.assertEqual(image.headers['Content-Type'], file_type)

            # Test deletion
            # Ensure file is present (it will be)
            self.assertTrue(grid.exists({'filename': filename}))
            # Delete the file and ensure it is not there through GridFS
            delete_upload(filename)
            # Ensure the file has gone
            self.assertFalse(grid.exists({'filename': filename}))

        # Ensure that if we load a non-image file a None value is returned
        image = io.BytesIO()
        self.assertIsNone(process_upload(image))
