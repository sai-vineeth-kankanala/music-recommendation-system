import datetime
from models import db

class ListeningHistory(db.Model):
    __tablename__ = 'listening_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id', ondelete='CASCADE'), nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    skipped = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'song_id': self.song_id,
            'played_at': self.played_at.isoformat(),
            'skipped': self.skipped
        }


class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # Rating scale 1-5
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Unique constraint on user_id and song_id
    __table_args__ = (
        db.UniqueConstraint('user_id', 'song_id', name='uq_user_song_rating'),
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='chk_rating_range')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'song_id': self.song_id,
            'rating': self.rating,
            'updated_at': self.updated_at.isoformat()
        }
