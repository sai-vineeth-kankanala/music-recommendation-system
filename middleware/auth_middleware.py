from functools import wraps
from flask import request, jsonify, g
import jwt
from config import get_config
from models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Format: Bearer <token>
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Bearer token required'}), 401
                
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            config = get_config()
            data = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
            # Load user
            user = User.query.filter_by(id=data['user_id']).first()
            if not user:
                return jsonify({'error': 'User not found'}), 401
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
            
        return f(*args, **kwargs)
        
    return decorated
