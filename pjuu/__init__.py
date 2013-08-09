# 3rd party imports
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from redis import Redis
# Pjuu imports
from lib.sessions import RedisSessionInterface


# Create application
app = Flask(__name__)
# Create Redis object so we can use db 1
redis = Redis(db=1)
# Set session handler to Redis
app.session_interface = RedisSessionInterface(redis=redis, prefix='')
# Create SQL alchemy
db = SQLAlchemy(app)

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)


# Import all Pjuu stuffs
import users
