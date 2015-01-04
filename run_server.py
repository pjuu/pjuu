#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
Description:
    Runs our development server!

    This is a CherryPy WSGIServer which is wrapped in side the Werkzeug
    DebuggedApplication middleware.

Licence:
    Copyright 2014-2015 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
