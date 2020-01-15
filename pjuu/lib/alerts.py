# -*- coding: utf8 -*-

"""Alert base classes and managers

To see how alerts are displayed to the user, see users.backend.get_alerts
and users.views.alerts.

For an example of how alerts are used look in users.backend and
posts.backend. Posts especially as this extends the alert object for its
own purposes.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
from collections import Iterable
# 3rd party imports
import jsonpickle
from werkzeug.utils import cached_property
# Pjuu imports
from pjuu import redis as r
from pjuu.auth.utils import get_user as be_get_user
from pjuu.lib import keys as k, timestamp, get_uuid


class BaseAlert(object):
    """Base form for all alerts within Pjuu.

    Note: This should not be used directly but subclassed.

    """

    def __init__(self, user_id):
        self.alert_id = get_uuid()
        self.timestamp = timestamp()
        self.user_id = user_id

    @cached_property
    def user(self):
        """Helper; Get the user object of the user who caused the alert.
        This value is cached in the interpreter so it doesn't go to the
        database each time this is called.

        """
        return be_get_user(self.user_id)

    def verify(self):
        """Check the alert is valid. You may need to overwrite this if you add
        anything to base alerts. See posts.backends.PostingAlert for more
        details on how to implement this.

        """
        # Simple implementation, check the user exists
        return self.user is not None

    def prettify(self, for_uid=None):
        """Overwrite to show how the alert will be presented to the user.

        For example:

            return "This is an alert about how cool Joe is :P"

        Feel free to use all functions you need to help make this happen.
        You may have to import some from Jinja2 and use url_for to get what we
        are looking for.

        """
        raise NotImplementedError


class AlertManager(object):
    """Handles storing, loading and dishing out alerts.

    """

    def get(self, aid):
        """Attempts to load an Alert from Redis and unpickle it.

        """
        # Try the unpickling process
        try:
            pickled_alert = r.get(k.ALERT.format(aid))
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
            r.delete(k.ALERT.format(aid))
            return None

    def alert(self, alert, user_ids):
        """Will attempt to alert the user with uid to the alert being managed.

        This will call the alerts before_alert() method, which allows you to
        change the alert per user. It's not needed though.

        """
        # Check that the manager actually has an alert
        if not isinstance(alert, BaseAlert):
            raise ValueError('alert must be a BaseAlert object')

        # Ensure uids is iterable
        # Stopped strings being passed in
        if not isinstance(user_ids, Iterable) or isinstance(user_ids, str):
            raise TypeError('user_ids must be iterable')

        # Create the alert object
        r.set(k.ALERT.format(alert.alert_id), jsonpickle.encode(alert))
        # Set the 4WK timeout on it
        r.expire(k.ALERT.format(alert.alert_id), k.EXPIRE_4WKS)

        for user_id in user_ids:
            r.zadd(k.USER_ALERTS.format(user_id), {
                str(alert.alert_id): alert.timestamp
            })
