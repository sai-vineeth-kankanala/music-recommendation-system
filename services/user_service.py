from models import db
from models.user import User, UserPreference
from models.recommendation import ListeningHistory, Rating
from models.song import Song
from utils.cache import cache
import datetime

class UserService:
    @staticmethod
    def get_profile(user_id):
        user = User.query.get(user_id)
        if not user:
            return None, "User not found."
        return user.to_dict(), None

    @staticmethod
    def update_profile(user_id, username, email):
        user = User.query.get(user_id)
        if not user:
            return None, "User not found."
            
        # Check if email is already taken by another user
        if email and email != user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                return None, "Email is already in use."
            user.email = email
            
        if username:
            user.username = username
            
        db.session.commit()
        return user.to_dict(), None

    @staticmethod
    def get_preferences(user_id):
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            return [], None
        return prefs.get_genres_list(), None

    @staticmethod
    def update_preferences(user_id, genres):
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserPreference(user_id=user_id)
            db.session.add(prefs)
            
        prefs.set_genres_list(genres)
        db.session.commit()
        
        # Invalidate recommendation caches for this user
        cache.delete_pattern(f"rec:{user_id}")
        
        return prefs.get_genres_list(), None

    @staticmethod
    def get_listening_history(user_id, limit=50):
        history = ListeningHistory.query.filter_by(user_id=user_id)\
            .order_by(ListeningHistory.played_at.desc())\
            .limit(limit).all()
            
        result = []
        for h in history:
            item = h.to_dict()
            item['song'] = h.song.to_dict() if h.song else None
            result.append(item)
        return result

    @staticmethod
    def add_listening_history(user_id, song_id, skipped=False):
        # Verify song exists
        song = Song.query.get(song_id)
        if not song:
            return None, "Song not found."
            
        history = ListeningHistory(user_id=user_id, song_id=song_id, skipped=skipped)
        db.session.add(history)
        
        # Update song popularity (frequency of play decreases weight if skipped, increases if played fully)
        # Simple popularity metric: total plays - skips
        plays = ListeningHistory.query.filter_by(song_id=song_id, skipped=False).count()
        skips = ListeningHistory.query.filter_by(song_id=song_id, skipped=True).count()
        song.popularity = float(max(0, plays - skips))
        
        db.session.commit()
        
        # Invalidate recommendation caches for this user
        cache.delete_pattern(f"rec:{user_id}")
        
        return history.to_dict(), None

    @staticmethod
    def add_rating(user_id, song_id, rating_value):
        # Verify song exists
        song = Song.query.get(song_id)
        if not song:
            return None, "Song not found."
            
        rating = Rating.query.filter_by(user_id=user_id, song_id=song_id).first()
        if rating:
            rating.rating = rating_value
            rating.updated_at = datetime.datetime.utcnow()
        else:
            rating = Rating(user_id=user_id, song_id=song_id, rating=rating_value)
            db.session.add(rating)
            
        db.session.commit()
        
        # Recalculate song popularity based on average rating
        # Popularity = average_rating * play_count
        avg_rating_query = db.session.query(db.func.avg(Rating.rating)).filter(Rating.song_id == song_id).scalar()
        avg_rating = float(avg_rating_query) if avg_rating_query else 0.0
        
        plays_count = ListeningHistory.query.filter_by(song_id=song_id, skipped=False).count()
        song.popularity = float(avg_rating * (1 + 0.1 * plays_count))
        
        db.session.commit()
        
        # Invalidate recommendation caches
        # Deleting all cache starting with rec: since collaborative filtering matrices might change
        cache.delete_pattern("rec:")
        
        return rating.to_dict(), None
