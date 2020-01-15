# -*- coding: utf8 -*-

"""This file is what should be imported to deploy Pjuu.

This is just a simple system for loading an application. If you rename this
file too .wsgi rather than .py it should work with Apache also.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Pjuu imports
from pjuu import create_app

# Create the Pjuu WSGI application
# You can pass in your production settings to the create_app() so you do not
# have to override any settings in settings.py :)
# This is the worlds most simple file. Looks at __init__ for more information.
# It is easy to load Pjuu with Gunicorn with pjuu.wsgi:application
# This file also allows easy deployment with mod_wsgi
application = create_app()
