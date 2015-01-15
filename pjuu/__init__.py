# -*- coding: utf8 -*-

"""The main Pjuu entry point. This module initializes everything as well as
provide the create_app() function to build an instance of Pjuu.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

# 3rd party imports
from flask import Flask
from flask_celery import Celery
from flask_mail import Mail
from flask_pymongo import PyMongo
from flask_redis import Redis
from raven.contrib.flask import Sentry
# Pjuu imports
from pjuu.lib.sessions import RedisSessionInterface


# Application information
__author__ = 'Joe Doherty <joe@pjuu.com>'
__version__ = '0.6.1'


# Global Flask-Mail object
mail = Mail()
# Global MongoDB object
mongo = PyMongo()
# Global Redis objects
# redis_sessions is only used by Flask for sessions
redis = Redis()
redis_sessions = Redis()
# Global Celery object
celery = Celery()
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

    # Initialize the PyMongo client
    mongo.init_app(app)

    # This is the _MAIN_ redis client. ONLY STORE DATA HERE
    redis.init_app(app)

    # Create Flask-Mail
    mail.init_app(app)

    # Create the Redis session interface
    redis_sessions.init_app(app, 'SESSION_REDIS')

    # Set session handler to Redis
    app.session_interface = RedisSessionInterface(redis=redis_sessions)

    # Create the applications Celery instance
    celery.init_app(app)

    with app.app_context():
        # Import all Pjuu stuffs
        # Load the blueprints
        from pjuu.pages import pages_bp
        app.register_blueprint(pages_bp)
        from pjuu.auth.views import auth_bp
        app.register_blueprint(auth_bp)
        from pjuu.posts.views import posts_bp
        app.register_blueprint(posts_bp)
        from pjuu.users.views import users_bp
        app.register_blueprint(users_bp)

    # Return a nice shiny new Pjuu WSGI application :)
    return app
