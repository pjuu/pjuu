#!/usr/bin/env python
import cherrypy
from pjuu import app

cherrypy.tree.mount(app, '/')
cherrypy.config.update({'engine.autoreload_on': False})

if __name__ == '__main__':
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
