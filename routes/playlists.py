from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from models import db
from models.playlist import Playlist, PlaylistSong
from models.song import Song

playlists_bp = Blueprint('playlists', __name__, url_prefix='/api/playlists')

@playlists_bp.route('', methods=['GET'])
@token_required
def get_playlists():
    playlists = Playlist.query.filter_by(user_id=g.current_user.id).all()
    return jsonify([p.to_dict() for p in playlists]), 200

@playlists_bp.route('', methods=['POST'])
@token_required
def create_playlist():
    data = request.get_json() or {}
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'error': 'Playlist name is required.'}), 400

    playlist = Playlist(user_id=g.current_user.id, name=name, description=description)
    db.session.add(playlist)
    db.session.commit()

    return jsonify({
        'message': 'Playlist created successfully.',
        'playlist': playlist.to_dict()
    }), 201

@playlists_bp.route('/<int:playlist_id>', methods=['GET'])
@token_required
def get_playlist(playlist_id):
    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        return jsonify({'error': 'Playlist not found.'}), 404

    if playlist.user_id != g.current_user.id:
        return jsonify({'error': 'You do not have permission to view this playlist.'}), 403

    return jsonify(playlist.to_dict()), 200

@playlists_bp.route('/<int:playlist_id>/songs', methods=['POST'])
@token_required
def add_song_to_playlist(playlist_id):
    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        return jsonify({'error': 'Playlist not found.'}), 404

    if playlist.user_id != g.current_user.id:
        return jsonify({'error': 'You do not have permission to modify this playlist.'}), 403

    data = request.get_json() or {}
    song_id = data.get('song_id')
    if not song_id:
        return jsonify({'error': 'song_id is required.'}), 400

    song = Song.query.get(song_id)
    if not song:
        return jsonify({'error': 'Song not found.'}), 404

    # Check if song is already in the playlist
    if song in playlist.songs:
        return jsonify({'error': 'Song is already in this playlist.'}), 400

    playlist.songs.append(song)
    db.session.commit()

    return jsonify({
        'message': 'Song added to playlist successfully.',
        'playlist': playlist.to_dict()
    }), 200
