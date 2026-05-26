from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.user_service import UserService
from utils.validators import validate_email, validate_username

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    user_dict, error = UserService.get_profile(g.current_user.id)
    if error:
        return jsonify({'error': error}), 404
    return jsonify(user_dict), 200

@users_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')

    if email and not validate_email(email):
        return jsonify({'error': 'Invalid email format.'}), 400

    if username and not validate_username(username):
        return jsonify({'error': 'Invalid username. Must be 3-50 alphanumeric characters.'}), 400

    user_dict, error = UserService.update_profile(g.current_user.id, username, email)
    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Profile updated successfully.',
        'user': user_dict
    }), 200

@users_bp.route('/preferences', methods=['GET'])
@token_required
def get_preferences():
    genres, error = UserService.get_preferences(g.current_user.id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'preferred_genres': genres}), 200

@users_bp.route('/preferences', methods=['PUT'])
@token_required
def update_preferences():
    data = request.get_json() or {}
    genres = data.get('preferred_genres')

    if genres is None or not isinstance(genres, list):
        return jsonify({'error': 'preferred_genres is required and must be a list of strings.'}), 400

    updated_genres, error = UserService.update_preferences(g.current_user.id, genres)
    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Preferences updated successfully.',
        'preferred_genres': updated_genres
    }), 200
