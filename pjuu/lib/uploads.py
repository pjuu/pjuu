# -*- coding: utf8 -*-

"""Handles processing and fetching of uploaded files.

At this time this only includes images so Wand and GridFS are used.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import io
from wand.image import Image
from wand.exceptions import MissingDelegateError
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

        # All images are passed through Wand and turned in to PNG files.
        # Unless the image is a GIF and its format is kept
        # Will change if they need thumbnailing or resizing.
        img = Image(file=upload)

        # If the input file if a GIF then we need to know
        gif = True if img.format == 'GIF' else False
        animated_gif = True if gif and len(img.sequence) > 1 else False

        # Check the exif data.
        # If there is an orientation then transform the image so that
        # it is always looking up.
        try:
            exif_data = {
                k[5:]: v
                for k, v in list(img.metadata.items())
                if k.startswith('exif:')
            }

            orientation = exif_data.get('Orientation')

            orientation = int(orientation)

            if orientation:  # pragma: no branch
                if orientation == 2:
                    img.flop()
                elif orientation == 3:
                    img.rotate(180)
                elif orientation == 4:
                    img.flip()
                elif orientation == 5:
                    img.flip()
                    img.rotate(90)
                elif orientation == 6:
                    img.rotate(90)
                elif orientation == 7:
                    img.flip()
                    img.rotate(270)
                elif orientation == 8:
                    img.rotate(270)

        except (AttributeError, TypeError, AttributeError):
            pass

        if thumbnail:
            # If the GIF was known to be animated then save the animated
            # then cycle through the frames, transforming them and save the
            # output
            if animated_gif:
                animated_image = Image()
                for frame in img.sequence:
                    frame.transform(resize='{0}x{1}>'.format(*image_size))
                    # Directly append the frame to the output image
                    animated_image.sequence.append(frame)

                animated_output = io.BytesIO()
                animated_output.format = 'GIF'
                animated_image.save(file=animated_output)
                animated_output.seek(0)

            img.transform(resize='{0}x{1}>'.format(*image_size))
        else:
            # Just sample the image to the correct size
            img.sample(*image_size)
            # Turn off animated GIF
            animated_gif = False

        img.format = 'PNG'
        uuid = get_uuid()
        filename = '{0}.{1}'.format(uuid, 'png')

        # Return the file pointer to the start
        img.save(file=output)
        output.seek(0)

        # Place file inside GridFS
        m.save_file(filename, output, base=collection)

        animated_filename = ''
        if animated_gif:
            animated_filename = '{0}.{1}'.format(uuid, 'gif')
            m.save_file(animated_filename, animated_output, base=collection)

        return filename, animated_filename
    except (IOError, MissingDelegateError):
        # File will not have been uploaded
        return None, None


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
