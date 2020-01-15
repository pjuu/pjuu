# -*- coding: utf8 -*-

"""Pjuu's session implementation.

This is a slightly modified version of one of the snippets provided by
Armin Ronacher @ flask.pocoo.org snippets

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# Stdlib imports
try:
    import pickle as pickle
except ImportError:  # pragma: no cover
    import pickle
from datetime import timedelta
from uuid import uuid4
# 3rd party imports
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

    def __init__(self, redis, prefix=''):
        self.redis = redis
        self.prefix = prefix

    def generate_sid(self):
        """
        Create a session id from the hex repr of a uuid1
        """
        return str(uuid4().hex)

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
            # I don't know why this stopped working
            if session.modified:  # pragma: no cover
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
