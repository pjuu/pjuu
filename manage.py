#!/usr/bin/env python
# 3rd party imports
from werkzeug.debug import DebuggedApplication
import cherrypy
from flask.ext.script import Manager, Server
# Pjuu imports
from pjuu import app


manager = Manager(app)


@manager.command
def runserver():
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


if __name__ == '__main__':
    manager.run()
