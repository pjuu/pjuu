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
    user_id = db.Column('user_id', db.Integer(unsigned=True),
                        db.ForeignKey('user.id'), index=True)
    created = db.Column(db.DateTime, default=datetime.now())
    body = db.Column(db.String(1024))

    def __init__(self, user, body):
        self.user_id = user.id
        self.body = body

    def __repr__(self):
        pass


class Comment(db.Model):
    '''
    Model for all comments on all posts.
    '''
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    user_id = db.Column('user_id', db.Integer(unsigned=True),
                        db.ForeignKey('user.id'), index=True)
    post_id = db.Column('post_id', db.Integer(unsigned=True),
                        db.ForeignKey('post.id'), index=True)
    created = db.Column(db.DateTime, default=datetime.now())
    body = db.Column(db.String(1024))

    def __init__(self, user, post, body):
        self.user_id = user.id
        self.post_id = post.id
        self.body = body

    def __repr__(self):
        pass
