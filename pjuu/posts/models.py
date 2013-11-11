# Pjuu imports
from pjuu import db


class Post(db.Model):
    '''
    Model for all text Posts made in Pjuu. This will be extended
    in future to support attachment images, video etc...
    '''
    __tablename__ = 'posts'
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    author = db.Column(db.Integer(unsigned=True),
                       db.ForeignKey('users.id'), index=True, nullable=False)
    created = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    body = db.Column(db.String(512), nullable=False)
    score = db.Column(db.BigInteger(unsigned=True), nullable=False, default=0)

    # Relationships
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
    __tablename__ = 'comments'
    id = db.Column(db.Integer(unsigned=True), primary_key=True)
    author = db.Column(db.Integer(unsigned=True),
                       db.ForeignKey('users.id'), index=True, nullable=False)
    created = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    body = db.Column(db.String(512), nullable=False)
    score = db.Column(db.BigInteger(unsigned=True), nullable=False, default=0)

    replyto = db.Column(db.Integer(unsigned=True),
                        db.ForeignKey('posts.id'), index=True, nullable=False)

    # Relationships
    # Overwrite `user` relationship as comments do not need a backref to this
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
