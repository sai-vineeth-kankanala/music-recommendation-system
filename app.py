import os
from flask import Flask, jsonify
from config import get_config
from models import db
from models.user import User, UserPreference
from models.song import Song
from models.playlist import Playlist, PlaylistSong
from models.recommendation import ListeningHistory, Rating
from middleware.error_handler import register_error_handlers
from services.song_service import SongService

# Import Blueprints
from routes.auth import auth_bp
from routes.users import users_bp
from routes.songs import songs_bp
from routes.playlists import playlists_bp
from routes.recommendations import recommendations_bp

def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = get_config()

    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(recommendations_bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Ensure DB tables exist and default songs are seeded
    with app.app_context():
        db.create_all()
        SongService.seed_default_songs()

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
