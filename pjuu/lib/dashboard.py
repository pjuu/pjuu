# -*- coding: utf8 -*-

"""Provides a dashboard to Pjuu's OP users `op` in MongoDB.

This should just give some stats on total users, total posts and new users etc.
This can be expanded in future to provide more of an admin area similar to
Django.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

import datetime
import importlib
import pkgutil
import os
import socket
import time

from flask import Blueprint, render_template, abort

import pjuu  # Used to finding stat imports
from pjuu.auth import current_user


dashboard_bp = Blueprint('dashboard', __name__)


def get_stats():
    """Dashboard provides server statistics as there is no better place to put
    this to have it appear at the top.

    """
    return [
        ('Hostname', socket.gethostname()),
        ('Uname', ' '.join(os.uname())),
        ('Time UTC', datetime.datetime.utcnow()),
        ('Timestamp', time.time()),
    ]


@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """The dashboard view will simply loop through the other packages looking
    for a `stats.py` which should contain all the statistics for that package
    that it would like to present on the dashboard.

    """
    # Do not allow users who are not OP to log in
    if not current_user or not current_user.get('op', False):
        return abort(403)

    # Get a list of all packages within Pjuu
    packages = [name
                for importer, name, ispkg
                in pkgutil.iter_modules(pjuu.__path__, pjuu.__name__ + ".")
                if ispkg
    ]

    # Hold on to all stats collected
    stats_list = []

    # Inject the server stats from this package
    stats_list.append(('server', get_stats()))

    # For each package look for the ``stats`` module and call ``get_stats``
    # If there isn't one it won't be added to the stats output
    for package_name in packages:
        try:
            package = importlib.import_module(package_name + ".stats")
        except ImportError:
            package = None

        if package is not None:
            try:
                # Split the package name to get sub-package name
                subpackage_name = package_name.split('.')
                subpackage_name = subpackage_name[len(subpackage_name) - 1]
                # Add the tuple to the list
                stats_list.append((subpackage_name, package.get_stats()))
            except AttributeError:  # pragma: no cover
                pass

    return render_template('dashboard.html', stats_list=stats_list)
