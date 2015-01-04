# -*- coding: utf8 -*-

"""Lua scripts for Redis.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2015 Joe Doherty

"""

from pjuu import redis as r


def zadd_member_nx(*args, **kwargs):
    """

    """
    func = r.register_script("""
    if not redis.call('ZRANK', KEYS[1], ARGV[2]) then
        redis.call('SET', 'HERE', 1)
        return redis.call('ZADD', KEYS[1], ARGV[1], ARGV[2])
    else
        return nil
    end
    """)

    return func(*args, **kwargs)
