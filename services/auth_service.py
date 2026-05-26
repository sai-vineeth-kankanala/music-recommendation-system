import datetime
import jwt
from models import db
from models.user import User, UserPreference
from config import get_config

class AuthService:
    @staticmethod
    def generate_tokens(user_id):
        """
        Generates access and refresh JWT tokens.
        """
        config = get_config()
        now = datetime.datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'exp': now + datetime.timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES),
            'iat': now,
            'type': 'access'
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'exp': now + datetime.timedelta(seconds=config.JWT_REFRESH_TOKEN_EXPIRES),
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, config.JWT_SECRET_KEY, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, config.JWT_SECRET_KEY, algorithm='HS256')
        
        return access_token, refresh_token

    @classmethod
    def register_user(cls, username, email, password):
        """
        Registers a new user and sets up their basic preference entry.
        """
        # Check if email exists
        if User.query.filter_by(email=email).first():
            return None, "Email already registered."
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush() # Populate ID without committing yet
        
        # Initialize default user preferences with empty string
        prefs = UserPreference(user_id=new_user.id, preferred_genres="")
        db.session.add(prefs)
        
        db.session.commit()
        return new_user.to_dict(), None

    @classmethod
    def login_user(cls, email, password):
        """
        Logs in user, verifies password, and generates tokens.
        """
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return None, "Invalid email or password."
            
        access_token, refresh_token = cls.generate_tokens(user.id)
        
        return {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }, None

    @classmethod
    def refresh_access_token(cls, r_token):
        """
        Generates a new access token from a valid refresh token.
        """
        config = get_config()
        try:
            payload = jwt.decode(r_token, config.JWT_SECRET_KEY, algorithms=["HS256"])
            if payload.get('type') != 'refresh':
                return None, "Invalid token type."
                
            user_id = payload.get('user_id')
            user = User.query.get(user_id)
            if not user:
                return None, "User not found."
                
            # Create a new access token only
            now = datetime.datetime.utcnow()
            access_payload = {
                'user_id': user_id,
                'exp': now + datetime.timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES),
                'iat': now,
                'type': 'access'
            }
            new_access_token = jwt.encode(access_payload, config.JWT_SECRET_KEY, algorithm='HS256')
            
            return {
                'access_token': new_access_token
            }, None
            
        except jwt.ExpiredSignatureError:
            return None, "Refresh token has expired."
        except jwt.InvalidTokenError:
            return None, "Invalid refresh token."
