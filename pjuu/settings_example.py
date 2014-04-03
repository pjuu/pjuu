# -*- coding: utf8 -*-

# Pjuu example settings file
# Please create a 'settings.py' from the template below

# Will show debug information when running in 'manage.py runserver'
DEBUG = True
# Pjuu will not send e-mails
NOMAIL = False

# Keep it secret, keep it safe
SECRET_KEY = 'Development Key'

# Redis settings (this is just the datastore, not sessions)
REDIS_HOST = 'redis'
REDIS_DB = 0

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
# Change these for extra security. Please see pjuu.auth.backend for details
TOKEN_KEY = SECRET_KEY
SALT_ACTIVATE = 'ACTIVATE'
SALT_FORGOT = 'FORGOT'
SALT_EMAIL = 'EMAIL'

# Logger file (this is for Warnings>)
LOG_FILE = ''
