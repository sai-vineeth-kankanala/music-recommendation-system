import json

def test_music_and_recommendation_flow(client):
    # 1. Register and login to get JWT token
    reg_payload = {
        "username": "musiclover",
        "email": "lover@example.com",
        "password": "Password123"
    }
    client.post('/api/auth/register', json=reg_payload)
    login_response = client.post('/api/auth/login', json={
        "email": "lover@example.com",
        "password": "Password123"
    })
    token = login_response.get_json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Get song list (database seeded auto on app launch)
    response = client.get('/api/songs', headers=headers)
    assert response.status_code == 200
    songs = response.get_json()
    assert len(songs) > 0
    song_id_1 = songs[0]['id']
    song_id_2 = songs[1]['id']
    song_id_3 = songs[2]['id']
    song_genre = songs[0]['genre']

    # 3. Get single song details
    response = client.get(f'/api/songs/{song_id_1}', headers=headers)
    assert response.status_code == 200
    song = response.get_json()
    assert song['id'] == song_id_1

    # 4. Search songs
    response = client.get(f'/api/songs/search?query={song["title"]}', headers=headers)
    assert response.status_code == 200
    search_results = response.get_json()
    assert len(search_results) > 0

    # 5. Get available genres
    response = client.get('/api/genres', headers=headers)
    assert response.status_code == 200
    genres = response.get_json()['genres']
    assert len(genres) > 0

    # 6. Set user preferences
    prefs_payload = {
        "preferred_genres": [song_genre]
    }
    response = client.put('/api/users/preferences', json=prefs_payload, headers=headers)
    assert response.status_code == 200

    # 7. Get trending recommendations
    response = client.get('/api/recommendations/trending', headers=headers)
    assert response.status_code == 200
    trending = response.get_json()
    assert len(trending) > 0

    # 8. Get similar songs
    response = client.get(f'/api/recommendations/similar/{song_id_1}', headers=headers)
    assert response.status_code == 200
    similar = response.get_json()
    assert len(similar) > 0

    # 9. Get curated for-you
    response = client.get('/api/recommendations/for-you', headers=headers)
    assert response.status_code == 200
    foryou = response.get_json()
    assert len(foryou) > 0

    # 10. Submit feedback (Rating 5 for song 1)
    feedback_payload = {
        "song_id": song_id_1,
        "rating": 5
    }
    response = client.post('/api/recommendations/feedback', json=feedback_payload, headers=headers)
    assert response.status_code == 200

    # 11. Submit play history (Played/Skipped feedback)
    play_payload = {
        "song_id": song_id_2,
        "skipped": False
    }
    response = client.post('/api/recommendations/feedback', json=play_payload, headers=headers)
    assert response.status_code == 200

    # 12. Submit skipped feedback for song 3
    skip_payload = {
        "song_id": song_id_3,
        "skipped": True
    }
    response = client.post('/api/recommendations/feedback', json=skip_payload, headers=headers)
    assert response.status_code == 200

    # 13. Get personalized recommendations
    response = client.get('/api/recommendations', headers=headers)
    assert response.status_code == 200
    recs = response.get_json()
    assert len(recs) > 0

    # 14. Playlist creation
    playlist_payload = {
        "name": "My Favorite Playlist",
        "description": "A collection of awesome songs"
    }
    response = client.post('/api/playlists', json=playlist_payload, headers=headers)
    assert response.status_code == 201
    playlist = response.get_json()['playlist']
    playlist_id = playlist['id']

    # 15. Add song to playlist
    add_song_payload = {
        "song_id": song_id_1
    }
    response = client.post(f'/api/playlists/{playlist_id}/songs', json=add_song_payload, headers=headers)
    assert response.status_code == 200
    playlist_updated = response.get_json()['playlist']
    assert len(playlist_updated['songs']) == 1
    assert playlist_updated['songs'][0]['id'] == song_id_1

    # 16. Get playlists list
    response = client.get('/api/playlists', headers=headers)
    assert response.status_code == 200
    playlists = response.get_json()
    assert len(playlists) > 0

    # 17. Get playlist details
    response = client.get(f'/api/playlists/{playlist_id}', headers=headers)
    assert response.status_code == 200

    # 18. YouTube route test with blacklist parameter
    response = client.get(f'/api/songs/{song_id_1}/youtube', headers=headers)
    assert response.status_code == 200
    res_data = response.get_json()
    first_yt_id = res_data.get('youtube_id')
    assert first_yt_id is not None

    # Request again with blacklist containing the first_yt_id
    response = client.get(f'/api/songs/{song_id_1}/youtube?blacklist={first_yt_id}', headers=headers)
    assert response.status_code == 200
    res_data_2 = response.get_json()
    second_yt_id = res_data_2.get('youtube_id')
    
    # Assert that the new YouTube ID is different (not the blacklisted one)
    assert second_yt_id != first_yt_id

    # 19. Delete song test
    response = client.delete(f'/api/songs/{song_id_1}', headers=headers)
    assert response.status_code == 200
    
    # Confirm it is deleted (returns 404)
    response = client.get(f'/api/songs/{song_id_1}', headers=headers)
    assert response.status_code == 404


def test_exclude_songs_without_youtube_id(client, app):
    # Register and login to get JWT token
    reg_payload = {
        "username": "filtertest",
        "email": "filter@example.com",
        "password": "Password123"
    }
    client.post('/api/auth/register', json=reg_payload)
    login_response = client.post('/api/auth/login', json={
        "email": "filter@example.com",
        "password": "Password123"
    })
    token = login_response.get_json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    with app.app_context():
        from models.song import Song
        from models import db
        
        # Create a song with empty/null youtube_id
        unplayable_song = Song(
            title="Unplayable Song",
            artist="Unplayable Artist",
            album="Test Album",
            genre="Pop",
            duration=180,
            youtube_id=""  # Empty YouTube ID
        )
        db.session.add(unplayable_song)
        db.session.commit()
        unplayable_id = unplayable_song.id

    # Verify that the unplayable song is not returned in the songs list
    response = client.get('/api/songs?limit=100', headers=headers)
    assert response.status_code == 200
    songs = response.get_json()
    song_ids = [s['id'] for s in songs]
    assert unplayable_id not in song_ids

    # Verify it is not returned in trending recommendations
    response = client.get('/api/recommendations/trending?limit=100', headers=headers)
    assert response.status_code == 200
    trending = response.get_json()
    trending_ids = [s['id'] for s in trending]
    assert unplayable_id not in trending_ids



