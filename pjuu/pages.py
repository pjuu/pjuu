# -*- coding: utf8 -*-

"""
Description:
   Handles Pjuu's non-dynamic pages.

   This may be changed in the future to support extra types of pages such as
   the help system etc...

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

# 3rd party imports
from flask import current_app as app, render_template


@app.route('/about')
def about():
    """About us

    """
    return render_template('pages/about.html')


@app.route('/terms')
def terms():
    """Terms of service

    """
    return render_template('pages/terms.html')


@app.route('/privacy')
def privacy():
    """Privacy policy

    """
    return render_template('pages/privacy.html')
