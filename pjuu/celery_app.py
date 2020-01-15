# -*- coding: utf8 -*-

"""Create a celery application for use with the celery worker

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from pjuu import create_app
from pjuu import celery


application = create_app()
application.app_context().push()

# Simply uses the import so it's not un-used
# There may be a nicer way of doing this `pragma: noqa` doesn't seem to work
celery = celery
