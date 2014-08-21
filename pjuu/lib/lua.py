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

# Redis LUA scripts
# Not all of these are used at the moment. I wrote them as they may be useful
# in the future if the Redis code inside Pjuu ever gets an overhaul.

# Thie script creates a new user, sets the passed in (lookup keys), and
# returns the new pid. This may seem overkill as we check the username and
# password prior to running this, it just stop a race condition
lua_create_user = """
if redis.call('EXISTS', KEYS[1]) == 0 and
   redis.call('EXISTS', KEYS[2]) == 0 then
    local pid = redis.call('INCR', 'global:uid')
    redis.call('SET', KEYS[1], pid)
    redis.call('SET', KEYS[2], pid)
    -- Ensure that the new account is set to expire
    redis.call('EXPIRE', KEYS[1], 86400)
    redis.call('EXPIRE', KEYS[2], 86400)
    return pid
else
    return nil
end
"""


# Load the above scripts in to Redis object r
create_user = r.register_script(lua_create_user)
