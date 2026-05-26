from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.recommendation_engine import RecommendationEngine
from services.user_service import UserService
from utils.validators import validate_rating

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

@recommendations_bp.route('', methods=['GET'])
@token_required
def get_personalized():
    limit = request.args.get('limit', 10, type=int)
    recommendations = RecommendationEngine.get_recommendations(g.current_user.id, limit=limit)
    return jsonify(recommendations), 200

@recommendations_bp.route('/for-you', methods=['GET'])
@token_required
def get_curated():
    limit = request.args.get('limit', 10, type=int)
    picks = RecommendationEngine.get_curated_picks(g.current_user.id, limit=limit)
    return jsonify(picks), 200

@recommendations_bp.route('/similar/<int:song_id>', methods=['GET'])
@token_required
def get_similar(song_id):
    limit = request.args.get('limit', 10, type=int)
    similar = RecommendationEngine.get_similar_songs(song_id, limit=limit)
    return jsonify(similar), 200

@recommendations_bp.route('/trending', methods=['GET'])
@token_required
def get_trending():
    limit = request.args.get('limit', 10, type=int)
    trending = RecommendationEngine.get_trending_songs(limit=limit)
    return jsonify(trending), 200

@recommendations_bp.route('/feedback', methods=['POST'])
@token_required
def submit_feedback():
    data = request.get_json() or {}
    song_id = data.get('song_id')
    rating = data.get('rating')
    skipped = data.get('skipped')

    if not song_id:
        return jsonify({'error': 'song_id is required.'}), 400

    response_data = {}

    # Log explicit rating if provided
    if rating is not None:
        if not validate_rating(rating):
            return jsonify({'error': 'Rating must be an integer between 1 and 5.'}), 400
        rating_dict, error = UserService.add_rating(g.current_user.id, song_id, int(rating))
        if error:
            return jsonify({'error': error}), 400
        response_data['rating'] = rating_dict

    # Log listening history/skip state if explicitly provided or if no rating is provided
    if skipped is not None or rating is None:
        is_skipped = bool(skipped) if skipped is not None else False
        history_dict, error = UserService.add_listening_history(g.current_user.id, song_id, is_skipped)
        if error:
            if not response_data:
                return jsonify({'error': error}), 400
        else:
            response_data['history'] = history_dict

    return jsonify({
        'message': 'Feedback submitted successfully.',
        'data': response_data
    }), 200
