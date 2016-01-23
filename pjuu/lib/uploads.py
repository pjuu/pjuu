# -*- coding: utf8 -*-

"""Handles processing and fetching of uploaded files.

At this time this only includes images so Pillow and GridFS are used.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import io
from PIL import Image as PILImage, ExifTags
import gridfs

from pjuu import mongo as m
from pjuu.lib import get_uuid


def process_upload(upload, collection='uploads', image_size=(1280, 720),
                   thumbnail=True):
    """Processes the uploaded images in the posts and also the users avatars.
    This should be extensible in future to support the uploading of videos,
    audio, etc...

    :param _id: The ID for the post, user or anything you want as the filename
    :type _id: str
    :param upload: The uploaded Werkzeug FileStorage object
    :type upload: ``Werkzeug.datastructures.FileStorage``
    :param collection: The GridFS collection to upload the file too.
    :type collection: str
    :param image_size: The max height and width for the upload
    :type image_size: Tuple length 2 of int
    :param thumbnail: Is the image to have it's aspect ration kept?
    :type thumbnail: bool
    """
    try:
        # StringIO to take the uploaded image to transport to GridFS
        output = io.BytesIO()

        # All images are passed through PIL and turned in to PNG files.
        # Will change if they need thumbnailing or resizing.
        img = PILImage.open(upload)

        # Check the exif data.
        # If there is an orientation then transform the image so that
        # it is always looking up.
        try:
            exif_data = {
                ExifTags.TAGS[k]: v
                for k, v in img._getexif().items()
                if k in ExifTags.TAGS
            }

            orientation = exif_data.get('Orientation')

            if orientation:  # pragma: no branch
                if orientation == 2:
                    img = img.transpose(PILImage.FLIP_LEFT_RIGHT)
                if orientation == 3:
                    img = img.transpose(PILImage.ROTATE_180)
                elif orientation == 4:
                    img = img.transpose(PILImage.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    img = img.transpose(PILImage.FLIP_TOP_BOTTOM)
                    img = img.transpose(PILImage.ROTATE_270)
                elif orientation == 6:
                    img = img.transpose(PILImage.ROTATE_270)
                elif orientation == 7:
                    img = img.transpose(PILImage.FLIP_TOP_BOTTOM)
                    img = img.transpose(PILImage.ROTATE_90)
                elif orientation == 8:
                    img = img.transpose(PILImage.ROTATE_90)

        except AttributeError:
            pass

        if thumbnail:
            img.thumbnail(image_size, PILImage.ANTIALIAS)
        else:
            # Pillow `resize` returns an image unlike thumbnail
            img = img.resize(image_size, PILImage.ANTIALIAS)

        img.save(output, format='PNG', quality=100)

        # Return the file pointer to the start
        output.seek(0)

        # Create a new file name <uuid>.<upload_extension>
        filename = '{0}.{1}'.format(get_uuid(), 'png')

        # Place file inside GridFS
        m.save_file(filename, output, base=collection)

        return filename
    except (IOError):
        # File will not have been uploaded
        return None


def get_upload(filename, collection='uploads', cache_for=3600):
    """Returns a Flask response object which should contain the uploaded file
    with filename from collection.

    This function will normally be hidden behind a Flask view which corresponds
    to what it is you are trying to get.

    :param filename: The filename to look for
    :param collection: The GridFS collection to look for filename in.

    """
    # Flask-PyMongo will handle 404's etc.
    return m.send_file(filename, base=collection, cache_for=cache_for)


def delete_upload(filename, collection='uploads'):
    """Deletes file with ``filename`` from GridFS ``collection.

    :param filename: The filename to delete
    :param collection: The collection to look for the file in

    """
    grid = gridfs.GridFS(m.db, collection=collection)

    # There should only be one file but unfortunately pymongo's docs are wrong
    # and there is no `find_one` method :(
    cursor = grid.find({'filename': filename})
    for file in cursor:
        return grid.delete(file._id)

    # If there is no file with the filename then return True.
    # This function does the same as the MongoDB, no files is always True.
    # This can't be hit without manually deleting the file from GridFS
    return True  # pragma: nocover
