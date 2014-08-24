# -*- coding: utf8 -*-

"""
Description:
    Alert related functions and constants.

    This is not in the users package to stop circular imports. The only
    function which is in the users package is get_alerts, this is too keep it
    consistent with the posts based functions.

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


from pjuu.lib import timestamp


def create_alert(uid, alert_reason, pid=None):
    """
    Create the initial alert. This will be in the form of a Python dictionary
    until it is converted in to a hash when the user is alerted.

    This will be in the form:
        $timestamp:$uid:$alert_reason[:$pid:$subscription_reason]

    Any additional info to save Redis lookups will be added as the alert is
    pushed out to the users alert feed.
    """
    # Ensure everything is an int.
    uid = int(uid)
    alert_reason = int(alert_reason)
    if pid:
        pid = int(pid)

    # Create initial empty dict
    alert = {}

    # Get the timestamp and add this to the alert. This WILL BE stored in the
    # hash but will also be used for the sorted sets score. This allows this
    # alert to appear in a users list, cronologically. There is is still race
    # conditions here, but it's only alerts, it does not really matter.
    alert['timestamp'] = timestamp()
    # Add the passed in information
    alert['uid'] = uid
    alert['alert_reason'] = alert_reason
    if pid:
        alert['pid'] = pid

    # Return our lovely alert dict
    return alert


def alert_user(uid, alert):
    """
    Will add alert (after its hashed) to the uid's alert feed.

    Additional information for the alert should be added here. At the moment
    this only includes the subscription_reason. I can't see us needing to add
    any more data soon.
    """
    pass


def make_alert_hash(alert):
    """
    Takes an alert dictionary and converts it to a hashed form:

        <value>[:<value>]*

    Note: The order is very important as there are no keywords.
          Please make sure you understand alert code properly before adding
          additional data. Additional data will need to be handled by all
          alert related functions.
    """
    # We are not going to monkey about with dealing with a improperly created
    # alert
    if type(alert) is not dict:
        # We are not returning none, if this happens THERE IS a programming
        # error and it needs to be fixed
        raise TypeError('Alert should be a dictionary')

    try:
        hash_str = ""
        hash_str += str(alert['timestamp'])
        hash_str += ':' + str(alert['uid'])
        hash_str += ':' + str(alert['alert_reason'])
        # If a pid is there add it :)
        if 'pid' in alert:
            hash_str += ':' + str(alert['pid'])
        # If there is a subscription_reason, add it!
        if 'subscription_reason' in alert:
            hash_str += ':' + str(alert['subscription'])
    except KeyError:
        # Oh no! It would appear the hash is not correctly formed
        # I know that we panic if the alert is not a dict but there could
        # be various reaons for this??? We will just return nothing
        return None

    # If were here we should now have a lovely hash string
    return hash_str


def parse_alert_hash(alert_hash):
    """
    Takes an alert hash of the form described in make_alert_hash() and turns
    it back into a Python dictionary. This make dealing with it a lot easier.
    """
    # Ensure alert_hash is a string
    alert_hash = str(alert_hash)

    # Our empty alert dict to parse the string in to
    alert = {}

    # Split on our colon seperator
    value_list = alert_hash.split(':')

    # Now we need to read the values back in
    try:
        alert['timestamp'] = int(value_list[0])
        alert['uid'] = int(value_list[1])
        alert['alert_reason'] = int(value_list[2])
        if len(value_list) >= 4:
            alert['pid'] = int(value_list[3])
        if len(value_list) >= 5:
            alert['subscription_reason'] = int(value_list[4])
    except IndexError:
        # Something went wrong, return nout
        return None

    return alert
