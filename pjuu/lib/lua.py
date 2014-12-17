# -*- coding: utf8 -*-

"""
Description:
    Lua scripts for Redis.

    This module should be run when the Pjuu application in created

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
