# Pjuu example settings file
# Please create a 'settings.py' from the template below
DEBUG = True

SECRET_KEY = 'Development Key'

# Flask-Mail
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = 'Pjuu <noreply@pjuu.com>'

# Flask-WTF
CSRF_ENABLE = True
CSRF_SESSION_KEY = SECRET_KEY

# Pagination
FEED_ITEMS_PER_PAGE = 50
PROFILE_ITEMS_PER_PAGE = 50

# Signer Keys
TOKEN_KEY = SECRET_KEY
SALT_ACTIVATE = ''
SALT_FORGOT = ''
SALT_EMAIL = ''
