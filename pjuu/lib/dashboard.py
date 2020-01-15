# -*- coding: utf8 -*-

"""Provides a dashboard to Pjuu's OP users.

Dashboard will loop through all packages under ``pjuu`` looking for `stats.py`
files and then will read in the stats (list of tuples) from `get_stats()`. It
then makes this data available on the site at '/dashboard'.

This package also provides generic server data to the dashboard itself. Things
such as hostname, uname, time, etc.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import datetime
import importlib
import pkgutil
import os
import socket
import sys
import time

from flask import Blueprint, render_template, abort

import pjuu  # Used to finding stat imports
from pjuu.auth import current_user


dashboard_bp = Blueprint('dashboard', __name__)


def get_stats():
    """Provides server statistics; hostname, uname, time (UTC) and timestamp.

    """
    return [
        ('Hostname', socket.gethostname()),
        ('Uname', ' '.join(os.uname())),
        ('Time UTC', datetime.datetime.utcnow()),
        ('Timestamp', time.time()),
        ('Python Version', "{}.{}.{}{}{}".format(*sys.version_info))
    ]


@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Loops through packages looking for stats to provide a data view.

    """
    # Do not allow users who are not OP to log in
    if not current_user or not current_user.get('op', False):
        return abort(403)

    # Get a list of all packages within Pjuu
    packages = [
        name
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
