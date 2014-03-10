# -*- coding: utf8 -*-

# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from redis import Redis
# Pjuu imports
from lib.sessions import RedisSessionInterface


__version__ = '0.1dev'


# Create application
app = Flask(__name__)
# This is the _MAIN_ redis client. ONLY STORE DATA HERE
redis = Redis(host='redis', db=0)
# Create Flask-Mail
mail = Mail(app)

# Create Redis objects (session store and data store)
redis_sessions = Redis(host='redis', db=1)
# Set session handler to Redis
app.session_interface = RedisSessionInterface(redis=redis_sessions, prefix='')

# Default config settings. Have to be changed here
# CSRF protection on by default
app.config['CSRF_ENABLE'] = True

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)


# LOGGING
# This is what will log errors in Pjuu to a standard logging handler
# This will not log in Debug mode as Werkzeug and stdout/stderr will
# TODO may require tweaks during productions
if not app.debug:
    import logging
    logging_handler = logging.FileHandler(app.config['LOG_FILE'])
    logging_handler.setLevel(logging.WARNING)
    logging_handler.setFormatter(logging.Formatter(
        '%(asctime)s: %(levelname)s: [%(pathname)s:%(lineno)d] %(message)s'
    ))
    app.logger.addHandler(logging_handler)


# Import all Pjuu stuffs
# errorhandler functions
import lib.errors
# Endpoints and brake out
import util
import users
import posts
