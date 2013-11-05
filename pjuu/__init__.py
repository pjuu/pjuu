# Stdlib imports
from hashlib import md5
import logging
# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import TimedSerializer
from redis import Redis
# Pjuu imports
from lib.sessions import RedisSessionInterface


# Create application
app = Flask(__name__)
# Create Redis objects
# Sessions
redis_sessions = Redis(db=1)
# Set session handler to Redis
app.session_interface = RedisSessionInterface(redis=redis_sessions, prefix='')
# Create Flask-Mail
mail = Mail(app)
# Create SQL alchemy
db = SQLAlchemy(app)
# Create cache

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)

# Import all Pjuu stuffs
import users
import posts
