# -*- coding: utf8 -*-

##############################################################################
# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.redis import Redis
from raven.contrib.flask import Sentry
# Pjuu imports
from lib.sessions import RedisSessionInterface


# Application information
__author__ = 'Joe Doherty <joe@pjuu.com>'
__version__ = '0.3dev'


# Global Flask-Mail object
mail = Mail()
# Global Redis objects
# redis_sessions is only used by Flask for sessions
redis = Redis()
redis_sessions = Redis()
# Raven global Sentry object for Flask
sentry = Sentry()


def create_app(config_filename='settings.py', config_dict={}):
    """
    Creates a Pjuu WSGI application with the passed in confif_filename.

    config_filename should be one of a Python file as per the default. To
    create one simply copy the settings.py file and change the settings
    to suit yourself

    settings_dict can be used to override any settings inside config_filename
    """
    # Create application
    app = Flask(__name__)

    # Load configuration from the Python file passed as config_filename
    app.config.from_pyfile(config_filename)
    # Override the settings from config_filename, even add new ones :)
    # This is useful for testing, we use it for Travis-CI, see run_tests.py
    app.config.update(config_dict)

    # This is the _MAIN_ redis client. ONLY STORE DATA HERE
    redis.init_app(app)

    # Create Flask-Mail
    mail.init_app(app)

    # Sentry logger
    # We now only use Sentry for logging all our in application errors
    # We do not need it if debug is True as we expect there could be errors
    # and we get full visibility.
    if not app.debug:
      sentry.init_app(app)

    # Create the Redis session interface
    redis_sessions.init_app(app, 'SESSION_REDIS')

    # Set session handler to Redis
    app.session_interface = RedisSessionInterface(redis=redis_sessions)

    with app.app_context():
        # Import all Pjuu stuffs
        # Load Redis LUA scripts, this will also load the scripts into Redis
        import lib.lua
        # Endpoints
        import auth.views
        import users.views
        import posts.views

    # Retrun a nice shiny new Pjuu WSGI application :)
    return app
