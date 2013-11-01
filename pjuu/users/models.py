# 3rd party imports
from werkzeug.security import generate_password_hash

# Pjuu imports
from pjuu import db


# Secondary table to store the Many-To-Many relationship of followers.
follow = db.Table('follow',
    db.Column('created', db.DateTime, default=db.func.now(),
              index=True, nullable=False),
    db.Column('user_id', db.Integer(unsigned=True), db.ForeignKey('user.id'),
              index=True, nullable=False),
    db.Column('followee_id', db.Integer(unsigned=True),
              db.ForeignKey('user.id'), index=True, nullable=False),
    db.UniqueConstraint('user_id', 'followee_id', name='uix_follow')
)


class User(db.Model):
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    username = db.Column(db.String(16), index=True, unique=True,
                         nullable=False)
    email = db.Column(db.String(254), index=True, unique=True,
                      nullable=False)
    password = db.Column(db.String(66))

    # Date stuff
    created = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    last_login = db.Column(db.DateTime)

    # Permissions stuff
    active = db.Column(db.Boolean, default=False, nullable=False)
    banned = db.Column(db.Boolean, default=False, nullable=False)
    op = db.Column(db.Boolean, default=False, nullable=False)

    # All users this User is following
    following = db.relationship('User',
        secondary=follow,
        primaryjoin=(follow.c.user_id == id),
        secondaryjoin=(follow.c.followee_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic')

    # Social stuff
    about = db.Column(db.String(512), default='', nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)

    def __repr__(self):
        return '<User %r>' % self.username
