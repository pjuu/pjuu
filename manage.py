#!/usr/bin/env python
# 3rd party imports
import cherrypy
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
# Pjuu imports
from pjuu import app, db

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def runserver():
    cherrypy.tree.graft(app, '/')
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
