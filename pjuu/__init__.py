# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
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

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)


@app.before_first_request
def before_first_request():
    print "BEFORE_FIRST_REQUEST"


@app.before_request
def before_request_debug():
    print "BEFORE_REQUEST"


@app.after_request
def after_request_debug(e):
    print "AFTER_REQUEST"
    return e


@app.teardown_request
def teardown_request_debug(e):
    print "TEARDOWN_REQUEST"


@app.teardown_appcontext
def teardown_appcontext_debug(e):
    print "TEARDOWN_APPCONTEXT"


# Import all Pjuu stuffs
import users
import posts
