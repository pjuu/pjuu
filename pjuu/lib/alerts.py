# -*- coding: utf8 -*-

"""
Description:
    Alert base classes and managers

    To see how alerts are displayed to the user, see users.backend.get_alerts
    and users.views.alerts.

    For an example of how alerts are used look in users.backend and
    posts.backend. Posts especially as this exdends the alert object for its
    own purposes.

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

# Stdlib imports
from base64 import b64decode, b64encode
# 3rd party imports
import jsonpickle
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K, lua as L, timestamp


class BaseAlert(object):
    """
    Base form for all alerts within Pjuu.
    """

    def __init__(self, uid):
        self.timestamp = timestamp()
        self.uid = int(uid)

    def get_username(self):
        """
        Helper; Get the username of the user who caused this.
        """
        return r.hget(K.USER % self.uid, 'username')

    def get_email(self):
        """
        Helper; Get the e-mail address of the user who caused this.
        """
        return r.hget(K.USER % self.uid, 'email')

    def before_alert(self, uid):
        """
        Called before the this alert is raised to the user with uid.

        self.uid is the user who created the alert (commenter, follower, etc.)
        uid this argument is the uid of the user who is going to have __this__
        alert added to there list.

        This can be used for such things as looking up subscription reasons
        and other stuff. You can update the alert from here before it is
        pickled.
        """
        raise NotImplementedError

    def prettify(self):
        """
        Overwrite to show how the alert will be presented to the user.

        For example:

            return "This is an alert about how cool Joe is :P"

        Feel free to use all functions you need to help make this happen.
        You may have to import some from Jinja2 and use url_for to get what we
        are looking for.
        """
        raise NotImplementedError


class AlertManager(object):
    """
    Handles storing, loading and dishing out alerts.

    An AlertManager should always be used in conjunction with an alert object.
    """

    def __init__(self, alert=None):
        # Throw an error if the alert is not BaseAlert
        if alert is not None and not isinstance(alert, BaseAlert):
            raise TypeError('Alert must be of type BaseAlert')
        # Store the alert or None if nothing was passed
        self.alert = alert

    def dumps(self):
        """
        If there is an alert, turn it into an encode pickle
        """
        if not self.alert:
            raise TypeError('make_pickle only works with an alert')
        # Pickle and b64 encode
        return b64encode(jsonpickle.encode(self.alert))

    def loads(self, pickled_alert):
        """
        Attempts to load an Alert from a pickled version
        """
        pickled_alert = str(pickled_alert)
        # Try the unpickling process
        try:
            _alert = jsonpickle.decode(b64decode(pickled_alert))
            # We need to ensure we get an alert back
            if isinstance(_alert, BaseAlert):
                self.alert = _alert
            # All okay
            return True
        except TypeError, ValueError:
            # Didn't work
            return False

    def alert_user(self, uid):
        """
        Will attempt to alert the user with uid to the alert being managed.

        This will call the alerts before_alert() method, which allows you to
        change the alert per user. It's not needed though.
        """
        # Add the timestamp at the time the user is alerted
        self.timestamp = timestamp()
        try:
            self.alert.before_alert(uid)
        except NotImplementedError:
            # Don't bother doing anything if before_alert is not there
            # it is not actually needed
            pass

        # Add the alert pickle to the user with uid
        r.zadd(K.USER_ALERTS % uid, self.alert.timestamp, self.dumps())
