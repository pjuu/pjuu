#!/usr/bin/env python
# -*- coding: utf8 -*-

# 3rd party imports
from werkzeug.debug import DebuggedApplication
import cherrypy
from flask.ext.script import Manager
# Pjuu imports
from pjuu import app


manager = Manager(app)


@manager.command
def runserver():
    """
    Run Pjuu inside a debug enabled CherryPy
    """
    debug_app = DebuggedApplication(app, True)
    cherrypy.tree.graft(debug_app, '/')
    cherrypy.config.update({
        'engine.autoreload_on': True,
        'log.screen': True,
        'server.socket_port': 5000,
        'server.socket_host': '0.0.0.0'
    })
    try:
        cherrypy.engine.start()
        cherrypy.engine.block()
    except KeyboardInterrupt:
        cherrypy.engine.stop()


@manager.command
def test():
    """
    Run all tests for Pjuu. These _HAVE_ to pass
    """
    return "Not implemented yet"


if __name__ == '__main__':
    manager.run()
