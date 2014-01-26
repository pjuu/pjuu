# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from itsdangerous import TimedSerializer
from redis import Redis
# Pjuu imports
from lib.sessions import RedisSessionInterface


# Create application
app = Flask(__name__)
# Create Redis objects (session store and data store)
redis_sessions = Redis(host='redis', db=0)
redis_store = Redis(host='redis', db=1)
# Create the shortcut `r`
r = redis_store
# Set session handler to Redis
app.session_interface = RedisSessionInterface(redis=redis_sessions, prefix='')
# Create Flask-Mail
mail = Mail(app)

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
