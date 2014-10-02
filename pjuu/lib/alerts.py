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
from collections import Iterable
from uuid import uuid1
# 3rd party imports
import jsonpickle
# Pjuu imports
from pjuu import redis as r
from pjuu.lib import keys as K, lua as L, timestamp


class BaseAlert(object):
    """
    Base form for all alerts within Pjuu.

    Note: This should not be used directly but subclassed.
    """

    def __init__(self, uid):
        self.aid = uuid1().int
        self.timestamp = timestamp()
        self.uid = uid

    def get_username(self):
        """
        Helper; Get the username of the user who caused this.
        """
        return r.hget(K.USER.format(self.uid), 'username')

    def get_email(self):
        """
        Helper; Get the e-mail address of the user who caused this.
        """
        return r.hget(K.USER.format(self.uid), 'email')

    def verify(self):
        """
        Check the alert is valid. You may need to overwrite this if you add
        anything to base alerts. See posts.backends.PostingAlert for more
        details on how to implement this.
        """
        # Simple implementation, check the user exists
        return r.exists(K.USER.format(self.uid))

    def prettify(self, for_uid=None):
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
    """

    def get(self, aid):
        """
        Attempts to load an Alert from Redis and unpickle it
        """
        # Try the unpickling process
        try:
            pickled_alert = r.get(K.ALERT.format(aid))
            alert = jsonpickle.decode(pickled_alert)
        except (TypeError, ValueError):
            # We failed to get an alert for whateva reason
            return None

        # Ensure we got an alert and that it verifies.
        if alert.verify():
            # Return the alert object
            return alert
        else:
            # If the alert did not verify delete it
            # This will stop this always being called
            r.delete(K.ALERT.format(aid))
            return None

    def alert(self, alert, uids):
        """
        Will attempt to alert the user with uid to the alert being managed.

        This will call the alerts before_alert() method, which allows you to
        change the alert per user. It's not needed though.
        """
        # Check that the manager actually has an alert
        if not isinstance(alert, BaseAlert):
            raise ValueError('AlertManager requires an alert to alert')

        # Ensure uids is iterable
        # Stopped strings being passed in
        if not isinstance(uids, Iterable) or isinstance(uids, str) or \
           isinstance(uids, unicode):
            raise TypeError('uids must be iterable')

        # Create the alert object
        r.set(K.ALERT.format(alert.aid), jsonpickle.encode(alert))
        # Set the 4WK timeout on it
        r.expire(K.ALERT.format(alert.aid), K.EXPIRE_4WKS)

        for uid in uids:
            # Only add the zset if the user still exists
            L.zadd_keyx(keys=(K.USER_ALERTS.format(uid), K.USER.format(uid)),
                        args=(alert.timestamp, alert.aid))
