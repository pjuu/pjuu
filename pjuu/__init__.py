# -*- coding: utf8 -*-

"""
Description:
    The main Pjuu entry point.

    This module initializes everything as well as provide the create_app
    function to build an instance of Pjuu.

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
from flask import Flask
from flask_mail import Mail
from flask_redis import Redis
from raven.contrib.flask import Sentry
# Pjuu imports
from .lib.sessions import RedisSessionInterface


# Application information
__author__ = 'Joe Doherty <joe@pjuu.com>'
__version__ = '0.5'


# Global Flask-Mail object
mail = Mail()
# Global Redis objects
# redis_sessions is only used by Flask for sessions
redis = Redis()
redis_sessions = Redis()
# Raven global Sentry object for Flask
sentry = Sentry()


def create_app(config_filename='settings.py', config_dict=None):
    """
    Creates a Pjuu WSGI application with the passed in confif_filename.

    config_filename should be one of a Python file as per the default. To
    create one simply copy the settings.py file and change the settings
    to suit yourself

    settings_dict can be used to override any settings inside config_filename.
    This is useful for testing. See run_tests.py for an example
    """
    # Pylint has suggested I dont set config_dict to a empty dict, we now have
    # to check if it is None and then assign an empty dict
    if config_dict is None:  # pragma: no cover
        config_dict = {}

    # Create application
    app = Flask(__name__)

    # Load configuration from the Python file passed as config_filename
    app.config.from_pyfile(config_filename)
    # Override the settings from config_filename, even add new ones :)
    # This is useful for testing, we use it for Travis-CI, see run_tests.py
    app.config.update(config_dict)

    # You can also set an environment variable called PJUU_SETTINGS this will
    # override all other Settings applied to Pjuu so long as you define them
    app.config.from_envvar('PJUU_SETTINGS', silent=True)

    # Sentry logger
    # We now only use Sentry for logging all our in application errors
    # We do not need it if debug is True as we expect there could be errors
    # and we get full visibility.
    if not app.debug:  # pragma: no cover
        sentry.init_app(app)

    # This is the _MAIN_ redis client. ONLY STORE DATA HERE
    redis.init_app(app)

    # Create Flask-Mail
    mail.init_app(app)

    # Create the Redis session interface
    redis_sessions.init_app(app, 'SESSION_REDIS')

    # Set session handler to Redis
    app.session_interface = RedisSessionInterface(redis=redis_sessions)

    with app.app_context():
        # Import all Pjuu stuffs
        # Load Redis LUA scripts, this will also load the scripts into Redis
        import pjuu.lib.lua
        # Endpoints
        import pjuu.pages
        import pjuu.auth.views
        import pjuu.users.views
        import pjuu.posts.views

    # Return a nice shiny new Pjuu WSGI application :)
    return app
