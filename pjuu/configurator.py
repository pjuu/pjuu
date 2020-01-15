# -*- coding: utf8 -*-

"""Exposes load() for reading the configuration similar to how Flask.config
does it.

We need to load the config before creating the Flask app for initializing
Celery.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

from flask.config import Config


def load(config_filename='settings.py'):
    """Create a Flask config that will be used to update the application
    config when it is created.

    - You can override most of the settings in `settings.py` using the
      environment.

    - You can set these on your system or use a file called `.env` in the root

    - You can override the actual loading of the default settings file by
      setting an environment variable `PJUU_SETTINGS` which points to a
      different file

    """
    config = Config("pjuu")

    # Load the default settings
    config.from_pyfile(config_filename)

    # Load the setting from the Environment variable
    config.from_envvar('PJUU_SETTINGS', silent=True)

    return config
