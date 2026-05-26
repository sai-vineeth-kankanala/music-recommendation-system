from models import db

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=True)
    genre = db.Column(db.String(100), nullable=True, index=True)
    duration = db.Column(db.Integer, nullable=False) # Duration in seconds
    
    # Audio Features (for recommendation engine content-based filtering)
    tempo = db.Column(db.Float, nullable=True)         # BPM (typically 50-200)
    energy = db.Column(db.Float, nullable=True)        # 0.0 to 1.0
    danceability = db.Column(db.Float, nullable=True)  # 0.0 to 1.0
    valence = db.Column(db.Float, nullable=True)       # 0.0 to 1.0 (musical positiveness)
    acousticness = db.Column(db.Float, nullable=True)  # 0.0 to 1.0
    
    popularity = db.Column(db.Float, default=0.0, nullable=True) # Normalized score (0-100 or 0-1)
    youtube_id = db.Column(db.String(100), nullable=True)

    # Relationships
    listening_history = db.relationship('ListeningHistory', backref='song', cascade="all, delete-orphan")
    ratings = db.relationship('Rating', backref='song', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'duration': self.duration,
            'youtube_id': self.youtube_id,
            'audio_features': {
                'tempo': self.tempo,
                'energy': self.energy,
                'danceability': self.danceability,
                'valence': self.valence,
                'acousticness': self.acousticness
            },
            'popularity': self.popularity
        }
