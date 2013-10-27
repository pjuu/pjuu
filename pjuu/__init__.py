# Stdlib imports
from hashlib import md5
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

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)


@app.template_filter('gravatar')
def gravatar(email, size=24):
    return 'https://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


# Import all Pjuu stuffs
import users
import posts
