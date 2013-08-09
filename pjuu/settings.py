# Pjuu settings file
import os
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

SECRET_KEY = 'Development Key'

# SQL Alchemy
SQLALCHEMY_DATABASE_URI = 'mysql://pjuu_dev@mysql.server:3306/pjuu_dev'

# WTForms
CSRF_ENABLE = True
CSRF_SESSION_KEY = SECRET_KEY
