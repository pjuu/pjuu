# -*- coding: utf8 -*-

"""Handles Pjuu's non-dynamic pages.

This may be changed in the future to support extra types of pages such as
the help system etc. May also become a package in its own right.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from flask import Blueprint, render_template


pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/about')
def about():
    """About us

    """
    return render_template('pages/about.html')


@pages_bp.route('/terms')
def terms():
    """Terms of service

    """
    return render_template('pages/terms.html')


@pages_bp.route('/privacy')
def privacy():
    """Privacy policy

    """
    return render_template('pages/privacy.html')


@pages_bp.route('/donations')
def donations():
    """Donations

    """
    return render_template('pages/donations.html')
