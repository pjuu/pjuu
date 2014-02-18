# -*- coding: utf8 -*-

# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from redis import Redis
# Pjuu imports
from lib.sessions import RedisSessionInterface


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


# Import all Pjuu stuffs
# errorhandler functions
import lib.errors
# Endpoints and brake out
import users
import posts
