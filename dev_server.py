#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Debugged WSGI Pjuu application for use my `make run`

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from werkzeug.debug import DebuggedApplication
from pjuu import create_app


application = DebuggedApplication(create_app(), True)
