# -*- coding: utf8 -*-

# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# 3rd party imports
from flask import Flask
from flask.ext.mail import Mail
from redis import Redis, StrictRedis
# Pjuu imports
from lib.sessions import RedisSessionInterface


# Application information
__author__ = 'Joe Doherty <joe@pjuu.com>'
__version__ = '0.1dev'


# Create application
app = Flask(__name__)

# Default config settings. Have to be changed here
# CSRF protection on by default
app.config['CSRF_ENABLE'] = True

# Load configuration from 'settings.py' and attempt to overwrite
# with file stored in PJUU_SETTINGS environment variable
app.config.from_object('pjuu.settings')
app.config.from_envvar('PJUU_SETTINGS', silent=True)

# This is the _MAIN_ redis client. ONLY STORE DATA HERE
redis = StrictRedis(host=app.config['REDIS_HOST'], db=app.config['REDIS_DB'],
                    decode_responses=True)
# Create Flask-Mail
mail = Mail(app)

# Create Redis objects (session store and data store)
redis_sessions = Redis(host=app.config['SESSION_REDIS_HOST'],
							 db=app.config['SESSION_REDIS_DB'])
# Set session handler to Redis
app.session_interface = RedisSessionInterface(redis=redis_sessions)


# LOGGING
# This is what will log errors in Pjuu to a standard logging handler
# This will not log in Debug mode as Werkzeug and stdout/stderr will
# TODO may require tweaks during productions
if not app.debug:
    import logging
    logging_handler = logging.FileHandler(app.config['LOG_FILE'])
    logging_handler.setLevel(logging.WARNING)
    logging_handler.setFormatter(logging.Formatter(
        "%(asctime)s: %(levelname)s: [%(pathname)s:%(lineno)d] %(message)s"
    ))
    app.logger.addHandler(logging_handler)


# Inject some Pjuu information in to Jinja
# All non-homed context-processors should live here
@app.context_processor
def inject_version():
    return dict(version=__version__)


# Import all Pjuu stuffs
# Error handlers
from lib.errors import *
# Endpoints
import auth
import users
import posts
