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

# Pjuu example settings file
# Please create a 'settings.py' from the template below
# Please make sure all settings have been updated for your
# development environment

# Will show debug information when running in 'manage.py runserver'
DEBUG = True
# Pjuu will not send e-mails
NOMAIL = False

# Keep it secret, keep it safe
# Ensure you change this!
SECRET_KEY = 'Development Key'

# Redis settings (this is just the datastore, not sessions)
REDIS_HOST = 'localhost'
REDIS_DB = 0

# Sessions
# Redis settings for sessions
SESSION_REDIS_HOST = 'localhost'
SESSION_REDIS_DB = 1

SESSION_COOKIE_HTTPONLY = True
# Ensure this is True in productions
# This will only work if communicating over HTTPS
SESSION_COOKIE_SECURE = False

# Flask-Mail
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = 'Pjuu <noreply@pjuu.com>'

# Flask-WTF (Cross site request forgery)
# Change this for extra security.
CSRF_SESSION_KEY = SECRET_KEY

# Recaptcha
# Add in your Recaptcha keys here
RECAPTCHA_USE_SSL = True
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = {
    'theme': 'white'
}

# Pagination
FEED_ITEMS_PER_PAGE = 25
PROFILE_ITEMS_PER_PAGE = 25

# Signer Keys
# Please see pjuu.auth.backend for details
TOKEN_KEY = SECRET_KEY
SALT_ACTIVATE = 'ACTIVATE'
SALT_FORGOT = 'FORGOT'
SALT_EMAIL = 'EMAIL'

# Logger file (this is for Warnings+)
# TODO allow changing this so you can use syslog, etc...
LOG_FILE = ''
