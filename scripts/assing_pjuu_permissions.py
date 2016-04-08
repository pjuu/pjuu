# -*- coding: utf8 -*-

"""Converts all posts in Pjuu to the new format used by the parser.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

# Add Pjuu in the parent directory to the path
import os
import sys
import inspect

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pymongo  # noqa

from pjuu import create_app, mongo as m  # noqa
from pjuu.lib import keys as k  # noqa


if __name__ == '__main__':
    # Set up Flask environment
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    for post in m.db.posts.find():
        post['permission'] = k.PERM_PJUU
        m.db.posts.update({'_id': post.get('_id')}, post)
