from flask import Blueprint, request, jsonify
from middleware.auth_middleware import token_required
from services.song_service import SongService

songs_bp = Blueprint('songs', __name__)

@songs_bp.route('/api/songs', methods=['GET'])
@token_required
def get_songs():
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    songs = SongService.get_songs(limit=limit, offset=offset)
    return jsonify(songs), 200

@songs_bp.route('/api/songs/<int:song_id>', methods=['GET', 'DELETE'])
@token_required
def get_song(song_id):
    if request.method == 'DELETE':
        success = SongService.delete_song(song_id)
        if not success:
            return jsonify({'error': 'Song not found.'}), 404
        return jsonify({'message': 'Song removed successfully.'}), 200
        
    song = SongService.get_song_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found.'}), 404
    return jsonify(song), 200


@songs_bp.route('/api/songs/search', methods=['GET'])
@token_required
def search_songs():
    query = request.args.get('query', request.args.get('q', ''))
    limit = request.args.get('limit', 20, type=int)
    songs = SongService.search_songs(query=query, limit=limit)
    return jsonify(songs), 200

@songs_bp.route('/api/genres', methods=['GET'])
@token_required
def get_genres():
    genres = SongService.get_genres()
    return jsonify({'genres': genres}), 200

@songs_bp.route('/api/songs/<int:song_id>/youtube', methods=['GET'])
@token_required
def get_song_youtube(song_id):
    blacklist = request.args.get('blacklist')
    yt_id = SongService.get_youtube_id(song_id, blacklist=blacklist)
    if not yt_id:
        return jsonify({'error': 'YouTube video not found.'}), 404
    return jsonify({'youtube_id': yt_id}), 200

