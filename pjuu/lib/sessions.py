# -*- coding: utf8 -*-

"""
Description:
    Pjuu's session implementation.

    This is a slightly modified version of one of the snippets provided by
    Armin Ronacher @ flask.pocoo.org snippets

Licence:
    Copyright 2014-2015 Joe Doherty <joe@pjuu.com>

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
try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle
from datetime import timedelta
from uuid import uuid1
# 3rd party imports
from redis import Redis
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin


class RedisSession(CallbackDict, SessionMixin):
    """
    How a session is stored inside Pjuu
    """

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True

        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class RedisSessionInterface(SessionInterface):
    """
    A replacement SessionInterface for Flask which allows us to store them
    inside our precious Redis :)
    """

    serializer = pickle
    session_class = RedisSession

    def __init__(self, redis=None, prefix=''):
        if redis is None:  # pragma: no cover
            redis = StrictRedis()
        self.redis = redis
        self.prefix = prefix

    def generate_sid(self):
        """
        Create a session id from the hex repr of a uuid1
        """
        return str(uuid1().hex)

    def get_redis_expiration_time(self, app, session):
        if session.permanent:
            return app.permanent_session_lifetime
        return timedelta(days=1)

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)

        # If there is no cookie identifying the session
        if not sid:
            sid = self.generate_sid()
            return self.session_class(sid=sid, new=True)

        # If there is a session id try and get the data
        val = self.redis.get(self.prefix + sid)
        if val is not None:
            data = self.serializer.loads(val)
            return self.session_class(data, sid=sid)

        # Create a new session if there is a sid but it holds nothing.
        # Ensure we create a new sid so we can't get session fixation
        return self.session_class(sid=self.generate_sid(), new=True)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            self.redis.delete(self.prefix + session.sid)
            if session.modified:
                response.delete_cookie(app.session_cookie_name, domain=domain)
            return
        redis_exp = self.get_redis_expiration_time(app, session)
        cookie_exp = self.get_expiration_time(app, session)
        val = self.serializer.dumps(dict(session))
        self.redis.setex(self.prefix + session.sid,
                         int(redis_exp.total_seconds()), val)
        # Secure cookies have been added to Armin's original snippet
        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=cookie_exp, domain=domain,
                            httponly=app.config['SESSION_COOKIE_HTTPONLY'],
                            secure=app.config['SESSION_COOKIE_SECURE'])
