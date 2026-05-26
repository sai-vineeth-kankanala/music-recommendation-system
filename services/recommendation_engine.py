import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from models import db
from models.song import Song
from models.user import UserPreference
from models.recommendation import ListeningHistory, Rating
from utils.cache import cache
from utils.constants import DEFAULT_CONTENT_WEIGHT, DEFAULT_COLLABORATIVE_WEIGHT
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    @staticmethod
    def _normalize_features(song):
        """
        Normalizes song audio features for similarity calculation.
        Normalizes tempo by dividing by 200 (assuming max BPM of 200).
        """
        return np.array([
            (song.tempo or 120.0) / 200.0,
            song.energy or 0.5,
            song.danceability or 0.5,
            song.valence or 0.5,
            song.acousticness or 0.5
        ])

    @classmethod
    def get_trending_songs(cls, limit=10):
        """
        Returns trending songs ordered by popularity score.
        """
        songs = Song.query.filter(Song.youtube_id != None, Song.youtube_id != '').order_by(Song.popularity.desc()).limit(limit).all()
        return [s.to_dict() for s in songs]

    @classmethod
    def get_similar_songs(cls, song_id, limit=10):
        """
        Content-based similarity search for a single song.
        """
        target_song = Song.query.get(song_id)
        if not target_song:
            return []

        # Get all other songs
        all_songs = Song.query.filter(Song.id != song_id, Song.youtube_id != None, Song.youtube_id != '').all()
        if not all_songs:
            return []

        # Vectorize target song
        target_vec = cls._normalize_features(target_song).reshape(1, -1)

        # Vectorize other songs
        other_vecs = np.array([cls._normalize_features(s) for s in all_songs])

        # Compute cosine similarities
        similarities = cosine_similarity(target_vec, other_vecs)[0]

        # Pair songs with similarity scores
        song_scores = list(zip(all_songs, similarities))
        song_scores.sort(key=lambda x: x[1], reverse=True)

        result = []
        for song, score in song_scores[:limit]:
            song_dict = song.to_dict()
            song_dict['similarity_score'] = float(score)
            result.append(song_dict)

        return result

    @classmethod
    def get_curated_picks(cls, user_id, limit=10):
        """
        Generates daily curated picks based on user preferences.
        """
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        preferred_genres = prefs.get_genres_list() if prefs else []

        if not preferred_genres:
            # Fallback to popular songs
            return cls.get_trending_songs(limit=limit)

        # Query songs matching preferences, order by popularity, and randomize slightly
        matched_songs = Song.query.filter(Song.genre.in_(preferred_genres), Song.youtube_id != None, Song.youtube_id != '').all()
        if not matched_songs:
            return cls.get_trending_songs(limit=limit)

        # Shuffle matched songs to make it feel "curated daily"
        random_seed = int(np.floor(np.floor(np.floor(np.floor(np.floor(1)))))) # placeholder
        import random
        random.shuffle(matched_songs)

        return [s.to_dict() for s in matched_songs[:limit]]

    @classmethod
    def get_recommendations(cls, user_id, limit=10):
        """
        A hybrid recommendation engine matching Content-based filtering
        and User-to-User collaborative filtering.
        """
        cache_key = f"rec:{user_id}:hybrid:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 1. Fetch user data
        history = ListeningHistory.query.filter_by(user_id=user_id).all()
        ratings = Rating.query.filter_by(user_id=user_id).all()
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        preferred_genres = prefs.get_genres_list() if prefs else []

        # List of song IDs the user has interacted with (exclude these from recommendations)
        interacted_song_ids = set(h.song_id for h in history) | set(r.song_id for r in ratings)

        # 2. Check if user is in a Cold-Start state (fewer than 3 ratings or plays)
        if len(ratings) < 3 and len(history) < 3:
            # Cold-start path: recommend based on preferred genres + global popularity
            recommendations = []
            if preferred_genres:
                genre_songs = Song.query.filter(
                    Song.genre.in_(preferred_genres),
                    Song.youtube_id != None,
                    Song.youtube_id != '',
                    ~Song.id.in_(interacted_song_ids) if interacted_song_ids else True
                ).order_by(Song.popularity.desc()).limit(limit).all()
                recommendations.extend(genre_songs)

            if len(recommendations) < limit:
                needed = limit - len(recommendations)
                exclude_ids = interacted_song_ids | set(s.id for s in recommendations)
                trending = Song.query.filter(
                    Song.youtube_id != None,
                    Song.youtube_id != '',
                    ~Song.id.in_(exclude_ids) if exclude_ids else True
                ).order_by(Song.popularity.desc()).limit(needed).all()
                recommendations.extend(trending)

            result = [s.to_dict() for s in recommendations[:limit]]
            cache.set(cache_key, result, timeout=300)
            return result

        # 3. Content-Based Filtering
        # Build User Audio Profile Vector from songs rated >= 4 or played and not skipped
        liked_song_ids = [r.song_id for r in ratings if r.rating >= 4]
        history_liked_song_ids = [h.song_id for h in history if not h.skipped]
        all_liked_ids = list(set(liked_song_ids + history_liked_song_ids))

        content_scores = {}
        if all_liked_ids:
            liked_songs = Song.query.filter(Song.id.in_(all_liked_ids), Song.youtube_id != None, Song.youtube_id != '').all()
            if liked_songs:
                liked_vectors = np.array([cls._normalize_features(s) for s in liked_songs])
                user_profile_vector = np.mean(liked_vectors, axis=0).reshape(1, -1)

                candidate_songs = Song.query.filter(~Song.id.in_(interacted_song_ids), Song.youtube_id != None, Song.youtube_id != '').all()
                if candidate_songs:
                    candidate_vectors = np.array([cls._normalize_features(s) for s in candidate_songs])
                    similarities = cosine_similarity(user_profile_vector, candidate_vectors)[0]
                    content_scores = {song.id: float(sim) for song, sim in zip(candidate_songs, similarities)}

        # 4. Collaborative Filtering (User-User CF)
        collab_scores = {}
        # Fetch all ratings to construct User-Item matrix
        all_ratings = Rating.query.all()
        if all_ratings:
            # List distinct user IDs and song IDs
            users_list = sorted(list(set(r.user_id for r in all_ratings)))
            songs_list = sorted(list(set(r.song_id for r in all_ratings)))

            user_idx = {uid: i for i, uid in enumerate(users_list)}
            song_idx = {sid: i for i, sid in enumerate(songs_list)}

            # Build matrix (users x songs)
            rating_matrix = np.zeros((len(users_list), len(songs_list)))
            for r in all_ratings:
                rating_matrix[user_idx[r.user_id], song_idx[r.song_id]] = r.rating

            # Calculate user similarity matrix using cosine similarity
            if user_id in user_idx:
                active_user_index = user_idx[user_id]
                user_similarities = cosine_similarity(rating_matrix)[active_user_index]

                # Identify unrated songs for the active user
                unrated_song_ids = [sid for sid in songs_list if sid not in interacted_song_ids]

                for sid in unrated_song_ids:
                    s_col_index = song_idx[sid]
                    # Find other users who rated this song
                    ratings_for_song = rating_matrix[:, s_col_index]
                    other_users_who_rated = np.where(ratings_for_song > 0)[0]

                    if len(other_users_who_rated) > 0:
                        # Weighted average rating based on user similarities
                        similarities_to_others = user_similarities[other_users_who_rated]
                        ratings_by_others = ratings_for_song[other_users_who_rated]

                        sum_sims = np.sum(np.abs(similarities_to_others))
                        if sum_sims > 0:
                            predicted_rating = np.sum(similarities_to_others * ratings_by_others) / sum_sims
                            # Normalize predicted rating (1-5) to 0-1 scale
                            collab_scores[sid] = (predicted_rating - 1) / 4.0

        # 5. Hybrid Combination
        candidate_songs = Song.query.filter(~Song.id.in_(interacted_song_ids), Song.youtube_id != None, Song.youtube_id != '').all()
        hybrid_rankings = []

        for song in candidate_songs:
            c_score = content_scores.get(song.id, 0.0)
            cf_score = collab_scores.get(song.id, 0.0)

            # Determine weights dynamically based on availability
            if song.id in content_scores and song.id in collab_scores:
                final_score = (DEFAULT_CONTENT_WEIGHT * c_score) + (DEFAULT_COLLABORATIVE_WEIGHT * cf_score)
            elif song.id in content_scores:
                final_score = c_score # Fallback completely to content similarity
            elif song.id in collab_scores:
                final_score = cf_score # Fallback to collaborative score
            else:
                # Cold fallback: use normalized song popularity
                final_score = min(1.0, (song.popularity or 0.0) / 100.0)

            hybrid_rankings.append((song, final_score))

        # Sort by final score descending
        hybrid_rankings.sort(key=lambda x: x[1], reverse=True)

        result = []
        for song, score in hybrid_rankings[:limit]:
            song_dict = song.to_dict()
            song_dict['recommendation_score'] = float(score)
            result.append(song_dict)

        cache.set(cache_key, result, timeout=300)
        return result
