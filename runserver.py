#!/usr/bin/env python
# -*- coding: utf8 -*-
# 3rd party imports
from werkzeug.debug import DebuggedApplication
import cherrypy
# Pjuu imports
from pjuu import app


if __name__ == '__main__':
    """
    Run Pjuu inside a debug enabled CherryPy.
    This is our test server. It is much more stable than Flasks,
    """
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
