# -*- coding: utf8 -*-

"""
Description:
    A small wrapper function for creating our Celery option.

    This must be called from within the create_app function so that it can use
    the application context.

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
from celery import Celery


def make_celery(app):
    """Create our celery object.

    This is taking from the documentation.

    """
    # Create our actual Celery object
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    # Update the config from the app's config
    celery.conf.update(app.config)

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        """Wrap the Celery task within the Flask application context.

        """
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    # Return the celery object
    return celery
