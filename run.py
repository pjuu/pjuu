#!/usr/bin/env python
from cherrypy import wsgiserver
from pjuu import app

if __name__ == '__main__':
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 5000), d)

    try:
        print "Server stated. Listening on http://0.0.0.0:5000"
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print "Server stopped"
