#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Runs the ``pjuu.lib.indexes.ensure_indexes()`` function.

Ensure indexes is in lib to aid in unit testing. This script allows this to be
run from outside of the application. This is useful for post deployment.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Pjuu imports
from pjuu import create_app
from pjuu.lib.indexes import ensure_indexes


if __name__ == '__main__':
    # Create the WSGI app and create the context
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    # Insert the indexes in to MongoDB
    ensure_indexes()

    # Get rid of the application context
    ctx.pop()
