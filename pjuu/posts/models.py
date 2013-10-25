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
    created = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    body = db.Column(db.String(512), nullable=False)

    user = db.relationship('User', backref=db.backref('posts',
                                                      order_by=created,
                                                      lazy="dynamic",
                                                      cascade="all,delete"))

    def __init__(self, user, body):
        self.author = user.id
        self.body = body

    def __repr__(self):
        return '<Post %r>' % self.id


class Comment(db.Model):
    '''
    Model for all text Comments made in Pjuu. This will be extended
    in future to support attachment images, video etc...
    '''
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    author = db.Column(db.Integer(unsigned=True),
                       db.ForeignKey('user.id'), index=True, nullable=False)
    replyto = db.Column(db.Integer(unsigned=True),
                        db.ForeignKey('post.id'), index=True, nullable=False)
    created = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    body = db.Column(db.String(512), nullable=False)

    # No backref needed for User to comments
    user = db.relationship('User')
    
    post = db.relationship('Post', backref=db.backref('comments',
                                                      order_by=created,
                                                      lazy="dynamic",
                                                      cascade="all,delete"))

    def __init__(self, user, replyto, body):
        self.author = user.id
        self.replyto = replyto
        self.body = body

    def __repr__(self):
        return '<Comment %r>' % self.id