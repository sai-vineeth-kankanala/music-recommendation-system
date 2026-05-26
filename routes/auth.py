from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from utils.validators import validate_email, validate_password, validate_username

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields: username, email, password'}), 400

    if not validate_username(username):
        return jsonify({'error': 'Invalid username. Must be 3-50 alphanumeric characters or spaces/hyphens/underscores.'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format.'}), 400

    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number.'}), 400

    user_dict, error = AuthService.register_user(username, email, password)
    if error:
        return jsonify({'error': error}), 409

    return jsonify({
        'message': 'User registered successfully.',
        'user': user_dict
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    login_data, error = AuthService.login_user(email, password)
    if error:
        return jsonify({'error': error}), 401

    return jsonify({
        'message': 'Login successful.',
        'user': login_data['user'],
        'access_token': login_data['access_token'],
        'refresh_token': login_data['refresh_token']
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': 'Refresh token is required.'}), 400

    refresh_data, error = AuthService.refresh_access_token(refresh_token)
    if error:
        return jsonify({'error': error}), 401

    return jsonify({
        'access_token': refresh_data['access_token']
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    # Since JWT is stateless, client deletes tokens. Backend confirms logout.
    return jsonify({
        'message': 'Logged out successfully.'
    }), 200
