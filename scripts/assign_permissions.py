# -*- coding: utf8 -*-

"""Moved the avatars form the `avatars` collection back to `uploads`.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import os
import sys
import inspect

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)


from pjuu import create_app, mongo as m  # noqa
from pjuu.lib.parser import parse_post  # noqa


if __name__ == '__main__':
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    print(m.db.posts.update(
        {'reply_to': {'$exists': False}},  # Update only posts
        {'$set': {'permission': 1}},  # Default PERM_PJUU
        upsert=False, multi=True
    ))
