from datetime import datetime
from hashlib import md5
from time import time
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import app, db, login
from sqlalchemy import update

##############################

followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

user_address_follow = db.Table(
    'followed_addresses',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('address_id', db.Integer, db.ForeignKey('address.id')),
    db.Column('new_tx', db.Integer, default=0)
)

##############################

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    addresses = db.relationship('Address', backref='author', lazy='dynamic')
    
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    
    followed_address = db.relationship(
        'Address', secondary = user_address_follow,
        #primaryjoin = (user_address_follow.c.user_id == id),
        #secondaryjoin = (user_address_follow.c.address_id == id),
        backref = db.backref('tracked_addresses', lazy='dynamic'),lazy='dynamic')
    

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.username.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    def tracked_addresses(self):
        return self.followed_address.filter(
                user_address_follow.c.user_id == self.id).all()
        
    def tracked_addresses_with_new_tx(self):
        return self.followed_address.filter(user_address_follow.c.new_tx == 1).all()


    def track_address(self, totrack):
        if not self.is_tracking_address(totrack):
            self.followed_address.append(totrack)
    
    def untrack_address(self, totrack):
        if self.is_tracking_address(totrack):
            self.followed_address.remove(totrack)

    def is_tracking_address(self, totrack):
        if totrack != None:
            return self.followed_address.filter(
                user_address_follow.c.address_id == totrack.id).count() > 0


    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(140))
    n_tx = db.Column(db.Integer)
    total_received = db.Column(db.String(140))
    total_sent = db.Column(db.String(140))
    last_tx = db.Column(db.DateTime, default=None)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    balance = db.Column(db.String(140))
    comment = db.Column(db.String(280))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Address {}>'.format(self.address)

    
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'))
    posted = db.Column(db.DateTime, default=datetime.utcnow)
    comment = db.Column(db.String)

    def __repr__(self):
        return '<Comment {}>'.format(self.comment)
