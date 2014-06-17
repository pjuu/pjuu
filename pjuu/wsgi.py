# -*- coding: utf8 -*-

"""
Description:
    This file is what should be imported to deploy Pjuu.

    This is just a simple system for loading an application. If you rename this
    file too .wsgi rather than .py it should work with Apache also.

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Pjuu imports
from pjuu import create_app

# Create the Pjuu WSGI application for mod_wsgi
# You can pass in your production settings to the create_app() so you do not
# have to override any settings in settings.py :)
application = create_app()