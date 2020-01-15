# -*- coding: utf8 -*-

"""Moved the avatars form the `avatars` collection back to `uploads`.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import io
import gridfs
from PIL import Image as PILImage
import pymongo


m = pymongo.MongoClient(host='127.0.0.1')


if __name__ == '__main__':
    out_grid = gridfs.GridFS(m.pjuu, collection='avatars')
    in_grid = gridfs.GridFS(m.pjuu, collection='uploads')

    for f in out_grid.find():
        out_file = out_grid.get(f._id)

        # Ensure the avatar is the correct size.
        output = io.BytesIO()

        img = PILImage.open(out_file)
        img = img.resize((96, 96), PILImage.ANTIALIAS)
        img.save(output, format='PNG', quality=100)
        output.seek(0)

        in_grid.put(output, filename=out_file.filename,
                    content_type=out_file.contentType)
        out_grid.delete(out_file._id)
