# -*- coding: utf8 -*-

# Attempt to load .env file
# Useful in development
from environs import Env
env = Env()
env.read_env()

# Will show debug information when running in 'manage.py runserver'
DEBUG = env.bool('DEBUG', True, )

# Are you testing Pjuu? This will prevent Flask-Mail sending any e-mails
# This is on by default so you do not need a e-mail server. To use auth tokens
# you can find them in Headers as X-Pjuu-Token on the return from a function.
# Note: It will be attached to the 302 is most cases so ensure you check the
# correct response to find this
TESTING = env.bool('TESTING', False)

# In the case of testing we need a server name, so here's one:
# SERVER_NAME = 'localhost'

# Keep it secret, keep it safe
# Ensure you change this!
SECRET_KEY = env.str('SECRET_KEY', 'ChangeMePlease')

# MongoDB Settings
MONGO_URI = env.str('MONGO_URI', 'mongodb://localhost:27017/pjuu')

# Redis settings (this is just the datastore, not sessions)
REDIS_URL = env.str('REDIS_URL', 'redis://localhost/0')
# Ensure that Unicode string are decoded
REDIS_DECODE_RESPONSES = True

# Sessions
# Redis settings for sessions
REDIS_SESSION_URL = env.str('REDIS_SESSION_URL', 'redis://localhost/1')

SESSION_COOKIE_HTTPONLY = True
# Ensure this is True in productions
# This will only work if communicating over HTTPS
SESSION_COOKIE_SECURE = env.bool('SECURE', False)

# Flask-Mail
# Ensure this is True in production to send e-mails
MAIL_SUPPRESS_SEND = DEBUG or TESTING
MAIL_SERVER = env.str('MAIL_SERVER', 'localhost')
MAIL_PORT = env.int('MAIL_PORT', 25)
MAIL_USE_TLS = env.bool('MAIL_USE_TLS', False)
MAIL_USE_SSL = env.bool('MAIL_USE_SSL', False)
MAIL_USERNAME = env.str('MAIL_USERNAME', None)
MAIL_PASSWORD = env.str('MAIL_PASSWORD', None)
MAIL_DEFAULT_SENDER = 'Pjuu <noreply@pjuu.com>'

# Flask-WTF (Cross site request forgery)
# CSRF should be off during testing to allow us to submit forms
WTF_CSRF_ENABLED = True
# Change this for extra security
WTF_CSRF_SESSION_KEY = SECRET_KEY

# Pagination
FEED_ITEMS_PER_PAGE = 25
REPLIES_ITEMS_PER_PAGE = 25
ALERT_ITEMS_PER_PAGE = 50

# Max search items is needed to work pagination across search terms
MAX_SEARCH_ITEMS = 500

# Line cap (the number of lines to show in a feed before 'Read more...' shows)
LINE_CAP = 5

# Sentry
SENTRY_DSN = env.str('SENTRY_DSN', '')

# Celery config
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', '')
CELERY_ALWAYS_EAGER = env.bool('CELERY_ALWAYS_EAGER', True)
