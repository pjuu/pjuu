# -*- coding: utf8 -*-

"""The main Pjuu entry point. This module initializes everything as well as
provide the create_app() function to build an instance of Pjuu.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import os

from flask import Flask, request, g
from flask_mail import Mail
from flask_pymongo import PyMongo
from flask_redis import Redis
from flask_wtf import CSRFProtect
from celery import Celery
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from pjuu.configurator import load as load_config
from pjuu.lib import timestamp
from pjuu.lib.sessions import RedisSessionInterface


# Application information
__author__ = 'Joe Doherty <joe@pjuu.com>'
__version__ = 'master'

# Load configuration
# We need this for initializing the Celery broker
config = load_config()

# Global Flask-Mail object
mail = Mail()
# Global MongoDB object
mongo = PyMongo()
# Global Redis objects
# redis_sessions is only used by Flask for sessions
redis = Redis()
redis_sessions = Redis()

celery = Celery(__name__, broker=config.get('CELERY_BROKER_URL', ''))

# Cross Site Request Forgery protection
csrf = CSRFProtect()


def create_app(config_dict=None):
    """Creates a Pjuu WSGI application with the passed in config_filename.

    ``config_filename`` should be a Python file as per the default. To
    create one simply copy the settings.py file and change the settings
    to suit yourself

    ``settings_dict`` can be used to override any settings inside
    ``config_filename``. This is useful for testing. See run_tests.py for an
    example
    """
    # Create application
    app = Flask(__name__)

    # Load the configuration from the previously created Config object
    app.config.update(config)

    # Override the settings, even add new ones :)
    # This is useful for testing, we use it for Travis-CI, see run_tests.py
    # Pylint has suggested I don't set config_dict to a empty dict, we now have
    # to check if it is None and then assign an empty dict
    if config_dict is not None:  # pragma: no cover
        app.config.update(config_dict)

    # Sentry
    if not app.debug:  # pragma: no cover
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()]
        )

    # Configure Celery
    celery.conf.update(app.config)

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    # Initialize the PyMongo client
    mongo.init_app(app)

    # This is the _MAIN_ redis client. ONLY STORE DATA HERE
    redis.init_app(app)

    # Create Flask-Mail
    mail.init_app(app)

    # Create the Redis session interface
    redis_sessions.init_app(app, 'REDIS_SESSION')

    # Initialize CSRF protection
    csrf.init_app(app)

    # Set session handler to Redis
    app.session_interface = RedisSessionInterface(redis=redis_sessions)

    # Generic handles
    @app.before_request
    def gather_time():
        """This is used to measure the request time for each page"""
        if app.debug and not app.testing:  # pragma: no cover
            if request.endpoint != 'static':
                g.start_time = timestamp()

    @app.after_request
    def display_time(response):
        """This is will write the time to the console in DEBUG mode"""
        if app.debug and not app.testing:  # pragma: no cover
            if request.endpoint != 'static':
                print(request.path, request.endpoint,
                      str((timestamp() - g.start_time) * 100) + 'ms')
        return response

    @app.url_defaults
    def cache_buster(endpoint, values):
        """Static URLs will have an mtime appended as a query string"""
        if 'static' == endpoint or '.static' == endpoint[-7:]:
            filename = values.get('filename', None)
            if filename:  # pragma: no branch
                static_folder = app.static_folder

                param_name = 'h'
                while param_name in values:
                    # Doesn't need coverage. Simple stops the param_name 'h'
                    # colliding with any future param
                    param_name = '_' + param_name  # pragma: no cover

                # Get the mtime of the file
                values[param_name] = int(os.stat(
                    os.path.join(static_folder, filename)).st_mtime)

    if not app.debug or (app.debug and app.testing):  # pragma: no branch
        # Register error handlers
        from pjuu.lib.errors import register_errors
        register_errors(app)

    # Import all Pjuu blue prints
    from pjuu.auth.views import auth_bp
    app.register_blueprint(auth_bp)
    from pjuu.posts.views import posts_bp
    app.register_blueprint(posts_bp)
    from pjuu.users.views import users_bp
    app.register_blueprint(users_bp)
    from pjuu.lib.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    from pjuu.lib.pages import pages_bp
    app.register_blueprint(pages_bp)

    # Return a nice shiny new Pjuu WSGI application :)
    return app
