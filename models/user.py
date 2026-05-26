import datetime
import bcrypt
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationships
    preferences = db.relationship('UserPreference', backref='user', uselist=False, cascade="all, delete-orphan")
    listening_history = db.relationship('ListeningHistory', backref='user', cascade="all, delete-orphan")
    ratings = db.relationship('Rating', backref='user', cascade="all, delete-orphan")
    playlists = db.relationship('Playlist', backref='user', cascade="all, delete-orphan")

    def set_password(self, password):
        salt = bcrypt.gensalt()
        # Hash password and store as string
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        self.password_hash = hashed.decode('utf-8')

    def check_password(self, password):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class UserPreference(db.Model):
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    preferred_genres = db.Column(db.Text, nullable=False) # Comma-separated genre list

    def get_genres_list(self):
        if not self.preferred_genres:
            return []
        return [g.strip() for g in self.preferred_genres.split(',') if g.strip()]

    def set_genres_list(self, genres):
        self.preferred_genres = ','.join([g.strip() for g in genres if g.strip()])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preferred_genres': self.get_genres_list()
        }
