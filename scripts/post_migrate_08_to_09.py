# -*- coding: utf8 -*-

"""Converts all posts in Pjuu to the new format used by the parser.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

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

from pjuu import create_app  # noqa
from pjuu.lib.parser import parse_post  # noqa


m = pymongo.MongoClient(host='localhost')


if __name__ == '__main__':
    # Set up Flask environment
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    for post in m.pjuu.posts.find():
        # Parse the posts body like it has just come in
        if post.get('links') is None and post.get('mentions') is None and \
                post.get('hashtags') is None:

            links, mentions, hashtags = parse_post(post.get('body'))

            if links:
                post['links'] = links
            if mentions:
                post['mentions'] = mentions
            if hashtags:
                post['hashtags'] = hashtags

            m.pjuu.posts.update({'_id': post.get('_id')},
                                post)
