# Stdlib imports
from datetime import datetime

# Pjuu imports
from pjuu import db


class Post(db.Model):
    '''
    Model for all text Posts made in Pjuu. This will be extended
    in future to support attachment images, video etc...
    '''
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    author = db.Column(db.Integer(unsigned=True),
                       db.ForeignKey('user.id'), index=True, nullable=False)
    replyto = db.Column(db.Integer(unsigned=True),
                        db.ForeignKey('post.id'), index=True, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    body = db.Column(db.String(512), nullable=False)

    def __init__(self, user, body, replyto=None):
        self.author = user.id
        self.replyto = replyto
        self.body = body

    def __repr__(self):
        return '<Post %r>' % id
