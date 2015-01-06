# -*- coding: utf8 -*-

# Pjuu example settings file
# Please copy this file and change the below for production

# Please make sure all settings have been updated for your
# development environment in this file! This file is used by run_server and
# also by run_tests, with run_tests it will automatically override some
# settings to allow the tests to run. See run_tests.py for more details

# Will show debug information when running in 'manage.py runserver'
DEBUG = True

# Are you testing Pjuu? This will prevent Flask-Mail sending any e-mails
# This is on by default so you do not need a e-mail server. To use auth tokens
# you can find them in Headers as X-Pjuu-Token on the return from a function.
# Note: It will be attached to the 302 is most cases so ensure you check the
# correct response to find this
TESTING = True

# In the case of testing we need a server name, so here's one:
# SERVER_NAME = 'localhost'

# Keep it secret, keep it safe
# Ensure you change this!
SECRET_KEY = 'Development Key'

# MongoDB Settings
MONGO_HOST = 'localhost'
MONGO_DBNAME = 'pjuu'

# Redis settings (this is just the datastore, not sessions)
REDIS_HOST = 'localhost'
REDIS_DB = 0
# Ensure that Unicode string are decoded
REDIS_DECODE_RESPONSES = True

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

# Celery
# This has gone in for future use. It is not currently implemented
CELERY_BROKER_URL = None
# We don't need a results backend. Our tasks are fire and forget
CELERY_RESULT_BACKEND = None
# Don't pass tasks down the broker by default
CELERY_ALWAYS_EAGER = True

# Flask-WTF (Cross site request forgery)
# CSRF should be off during testing to allow us to submit forms
WTF_CSRF_ENABLED = True
# Change this for extra security
WTF_CSRF_SESSION_KEY = SECRET_KEY

# Sentry settings
# If you do not add a Sentry DSN you will not receive any logging information
# If you do not run Sentry then you can add a custom logger in see the Flask
# documentation: http://flask.pocoo.org/docs/errorhandling/
# You will need to do add a custom one inside the __init__.py file within the
# create_app() function.
SENTRY_DSN = ''

# Pagination
FEED_ITEMS_PER_PAGE = 25
PROFILE_ITEMS_PER_PAGE = 25
ALERT_ITEMS_PER_PAGE = 50
