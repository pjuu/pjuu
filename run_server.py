#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Runs our development server! This is a CherryPy WSGIServer which is wrapped
inside the Werkzeug DebuggedApplication middleware.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

# 3rd party imports
from werkzeug.debug import DebuggedApplication
import cherrypy
# Pjuu imports
from pjuu import create_app


if __name__ == '__main__':
    """
    Run Pjuu inside a debug enabled CherryPy.
    This is our test server. It is much more stable than Flasks.

    By default we bind this to all IPs so that we can test the
    the dev site with our phones over the local network
    """
    app = create_app()
    debug_app = DebuggedApplication(app, True)
    cherrypy.tree.graft(debug_app, '/')
    cherrypy.config.update({
        'engine.autoreload_on': True,
        'server.socket_port': 5000,
        'server.socket_host': '0.0.0.0'
    })
    try:
        cherrypy.engine.start()
        cherrypy.engine.block()
    except KeyboardInterrupt:
        cherrypy.engine.stop()
