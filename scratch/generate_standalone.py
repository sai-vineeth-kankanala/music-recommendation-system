import json
import re

def main():
    print("Reading index.html...")
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    print("Reading songs.json...")
    with open("scratch/songs.json", "r", encoding="utf-8") as f:
        songs = json.load(f)

    # Let's clean the songs data to be lightweight
    cleaned_songs = []
    for s in songs:
        cleaned_songs.append({
            'id': s['id'],
            'title': s['title'],
            'artist': s['artist'],
            'album': s['album'],
            'genre': s['genre'],
            'duration': s['duration'],
            'youtube_id': s['youtube_id'],
            'tempo': s['audio_features']['tempo'],
            'energy': s['audio_features']['energy'],
            'danceability': s['audio_features']['danceability'],
            'valence': s['audio_features']['valence'],
            'acousticness': s['audio_features']['acousticness'],
            'popularity': s['popularity']
        })

    # Javascript helpers for recommendations and cosine similarity
    js_helpers = """
        // Client-side standalone data & recommendation logic
        let allSongs = """ + json.dumps(cleaned_songs, ensure_ascii=False) + """;

        function getCosineSimilarity(v1, v2) {
            let dotProduct = 0.0;
            let normA = 0.0;
            let normB = 0.0;
            for (let i = 0; i < v1.length; i++) {
                dotProduct += v1[i] * v2[i];
                normA += v1[i] * v1[i];
                normB += v2[i] * v2[i];
            }
            if (normA === 0.0 || normB === 0.0) return 0.0;
            return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
        }

        function normalizeFeatures(song) {
            return [
                (song.tempo || 120.0) / 200.0,
                song.energy || 0.5,
                song.danceability || 0.5,
                song.valence || 0.5,
                song.acousticness || 0.5
            ];
        }
    """

    # Inject variables right inside the script tag start
    # Let's locate the first script tag after styles
    script_start = html.find("<script>")
    if script_start != -1:
        html = html[:script_start + 8] + js_helpers + html[script_start + 8:]
    else:
        print("Error: Could not find script start tag!")
        return

    # Replace apiRequest implementation
    api_request_regex = r"async function apiRequest\(path,\s*method\s*=\s*'GET',\s*body\s*=\s*null\)\s*\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}"
    
    mock_api_request = """async function apiRequest(path, method = 'GET', body = null) {
            // Wait slightly to simulate server delay
            await new Promise(resolve => setTimeout(resolve, 80));
            
            try {
                // Auth check
                const isAuthPath = path.startsWith('/api/auth');
                if (!isAuthPath && !authToken) {
                    throw new Error("Unauthorized");
                }
                
                // 1. LOGIN
                if (path === '/api/auth/login' && method === 'POST') {
                    const users = JSON.parse(localStorage.getItem('users') || '[]');
                    const user = users.find(u => u.email === body.email && u.password === body.password);
                    if (!user) {
                        throw new Error('Invalid email or password.');
                    }
                    return { access_token: `mock_jwt_${user.id}`, user };
                }
                
                // 2. REGISTER
                if (path === '/api/auth/register' && method === 'POST') {
                    const users = JSON.parse(localStorage.getItem('users') || '[]');
                    if (users.find(u => u.email === body.email)) {
                        throw new Error('Email already registered.');
                    }
                    const newUser = { id: Date.now(), username: body.username, email: body.email, password: body.password };
                    users.push(newUser);
                    localStorage.setItem('users', JSON.stringify(users));
                    return { message: 'Registration successful.' };
                }
                
                // 3. PROFILE
                if (path === '/api/users/profile' && method === 'GET') {
                    const tokenParts = authToken.split('_');
                    const userId = parseInt(tokenParts[tokenParts.length - 1]);
                    const users = JSON.parse(localStorage.getItem('users') || '[]');
                    const user = users.find(u => u.id === userId);
                    if (!user) throw new Error('User not found.');
                    return user;
                }
                
                // 4. SONGS
                if (path.startsWith('/api/songs') && method === 'GET') {
                    if (path.includes('/youtube')) {
                        // e.g., /api/songs/12/youtube?blacklist=...
                        const urlParts = path.split('/');
                        const songId = parseInt(urlParts[3]);
                        const queryParams = new URLSearchParams(path.split('?')[1] || '');
                        const blacklistStr = queryParams.get('blacklist') || '';
                        const blacklist = blacklistStr.split(',').filter(Boolean);
                        
                        const song = allSongs.find(s => s.id === songId);
                        if (!song) throw new Error('Song not found');
                        
                        if (song.youtube_id && !blacklist.includes(song.youtube_id)) {
                            return { youtube_id: song.youtube_id };
                        }
                        
                        // Search alternative fallbacks
                        const mockAltId = `dQw4w9WgXcQ`; // Rick roll fallback
                        return { youtube_id: mockAltId };
                    }
                    if (path.startsWith('/api/songs/search')) {
                        const queryParams = new URLSearchParams(path.split('?')[1] || '');
                        const q = (queryParams.get('query') || '').toLowerCase();
                        const matches = allSongs.filter(s => 
                            s.youtube_id && (
                                s.title.toLowerCase().includes(q) || 
                                s.artist.toLowerCase().includes(q) || 
                                s.genre.toLowerCase().includes(q)
                            )
                        );
                        return matches.slice(0, 30);
                    }
                    // Get all songs: /api/songs?limit=50
                    const playable = allSongs.filter(s => s.youtube_id);
                    return playable.slice(0, 50);
                }
                
                // DELETE song
                if (path.startsWith('/api/songs/') && method === 'DELETE') {
                    const songId = parseInt(path.split('/')[3]);
                    allSongs = allSongs.filter(s => s.id !== songId);
                    return { message: 'Song deleted.' };
                }
                
                // 5. GENRES
                if (path === '/api/genres' && method === 'GET') {
                    const genres = Array.from(new Set(allSongs.map(s => s.genre)));
                    return { genres };
                }
                
                // 6. USER PREFERENCES
                if (path === '/api/users/preferences') {
                    const tokenParts = authToken.split('_');
                    const userId = tokenParts[tokenParts.length - 1];
                    if (method === 'GET') {
                        const prefs = JSON.parse(localStorage.getItem(`prefs_${userId}`) || '{}');
                        return prefs;
                    }
                    if (method === 'PUT') {
                        localStorage.setItem(`prefs_${userId}`, JSON.stringify(body));
                        return { message: 'Preferences updated.' };
                    }
                }
                
                // 7. RECOMMENDATIONS
                if (path.startsWith('/api/recommendations')) {
                    const tokenParts = authToken.split('_');
                    const userId = tokenParts[tokenParts.length - 1];
                    
                    if (path.includes('/trending')) {
                        const limit = 6;
                        const songs = allSongs.filter(s => s.youtube_id);
                        songs.sort((a, b) => b.popularity - a.popularity);
                        return songs.slice(0, limit);
                    }
                    if (path.includes('/for-you')) {
                        const limit = 6;
                        const prefs = JSON.parse(localStorage.getItem(`prefs_${userId}`) || '{}');
                        const preferredGenres = prefs.preferred_genres || [];
                        if (preferredGenres.length === 0) {
                            const songs = allSongs.filter(s => s.youtube_id);
                            songs.sort((a, b) => b.popularity - a.popularity);
                            return songs.slice(0, limit);
                        }
                        const matched = allSongs.filter(s => preferredGenres.includes(s.genre) && s.youtube_id);
                        // Shuffle matched
                        const shuffled = [...matched].sort(() => 0.5 - Math.random());
                        return shuffled.slice(0, limit);
                    }
                    if (path.includes('/similar/')) {
                        const songId = parseInt(path.split('/').pop().split('?')[0]);
                        const limit = 4;
                        
                        const targetSong = allSongs.find(s => s.id === songId);
                        if (!targetSong) return [];
                        
                        const targetVec = normalizeFeatures(targetSong);
                        const otherSongs = allSongs.filter(s => s.id !== songId && s.youtube_id);
                        
                        const scores = otherSongs.map(s => {
                            const sVec = normalizeFeatures(s);
                            const score = getCosineSimilarity(targetVec, sVec);
                            return { ...s, similarity_score: score };
                        });
                        
                        scores.sort((a, b) => b.similarity_score - a.similarity_score);
                        return scores.slice(0, limit);
                    }
                    if (path.includes('/feedback') && method === 'POST') {
                        const historyKey = `history_${userId}`;
                        const history = JSON.parse(localStorage.getItem(historyKey) || '[]');
                        history.push({ song_id: body.song_id, skipped: !!body.skipped, timestamp: Date.now() });
                        localStorage.setItem(historyKey, JSON.stringify(history));
                        
                        if (body.rating) {
                            const ratingsKey = `ratings_${userId}`;
                            const ratings = JSON.parse(localStorage.getItem(ratingsKey) || '[]');
                            const filtered = ratings.filter(r => r.song_id !== body.song_id);
                            filtered.push({ song_id: body.song_id, rating: body.rating });
                            localStorage.setItem(ratingsKey, JSON.stringify(filtered));
                        }
                        return { message: 'Feedback logged.' };
                    }
                    
                    // Main hybrid recommendations: /api/recommendations?limit=6
                    const limit = 6;
                    const historyKey = `history_${userId}`;
                    const ratingsKey = `ratings_${userId}`;
                    const history = JSON.parse(localStorage.getItem(historyKey) || '[]');
                    const ratings = JSON.parse(localStorage.getItem(ratingsKey) || '[]');
                    const prefs = JSON.parse(localStorage.getItem(`prefs_${userId}`) || '{}');
                    const preferredGenres = prefs.preferred_genres || [];
                    
                    const interactedIds = new Set([
                        ...history.map(h => h.song_id),
                        ...ratings.map(r => r.song_id)
                    ]);
                    
                    if (ratings.length < 3 && history.length < 3) {
                        let recs = [];
                        if (preferredGenres.length > 0) {
                            recs = allSongs.filter(s => preferredGenres.includes(s.genre) && !interactedIds.has(s.id) && s.youtube_id);
                            recs.sort((a, b) => b.popularity - a.popularity);
                        }
                        if (recs.length < limit) {
                            const needed = limit - recs.length;
                            const excludeIds = new Set([...recs.map(s => s.id), ...interactedIds]);
                            const trending = allSongs.filter(s => !excludeIds.has(s.id) && s.youtube_id);
                            trending.sort((a, b) => b.popularity - a.popularity);
                            recs = recs.concat(trending.slice(0, needed));
                        }
                        return recs.slice(0, limit).map(s => ({ ...s, recommendation_score: s.popularity / 100 }));
                    }
                    
                    const likedIds = new Set([
                        ...ratings.filter(r => r.rating >= 4).map(r => r.song_id),
                        ...history.filter(h => !h.skipped).map(h => h.song_id)
                    ]);
                    
                    let userProfile = [0.5, 0.5, 0.5, 0.5, 0.5];
                    if (likedIds.size > 0) {
                        const vectors = Array.from(likedIds).map(id => {
                            const s = allSongs.find(song => song.id === id);
                            return s ? normalizeFeatures(s) : [0.5, 0.5, 0.5, 0.5, 0.5];
                        });
                        userProfile = vectors[0].map((_, idx) => vectors.reduce((sum, v) => sum + v[idx], 0) / vectors.length);
                    }
                    
                    const candidates = allSongs.filter(s => !interactedIds.has(s.id) && s.youtube_id);
                    const scored = candidates.map(s => {
                        const sVec = normalizeFeatures(s);
                        const score = getCosineSimilarity(userProfile, sVec);
                        return { ...s, recommendation_score: score };
                    });
                    
                    scored.sort((a, b) => b.recommendation_score - a.recommendation_score);
                    return scored.slice(0, limit);
                }
                
                // 8. PLAYLISTS
                if (path === '/api/playlists') {
                    const tokenParts = authToken.split('_');
                    const userId = tokenParts[tokenParts.length - 1];
                    const playlistsKey = `playlists_${userId}`;
                    
                    if (method === 'GET') {
                        return JSON.parse(localStorage.getItem(playlistsKey) || '[]');
                    }
                    if (method === 'POST') {
                        const playlists = JSON.parse(localStorage.getItem(playlistsKey) || '[]');
                        const newPlaylist = {
                            id: Date.now(),
                            user_id: parseInt(userId),
                            name: body.name,
                            description: body.description,
                            created_at: new Date().toISOString(),
                            songs: []
                        };
                        playlists.push(newPlaylist);
                        localStorage.setItem(playlistsKey, JSON.stringify(playlists));
                        return { message: 'Playlist created.', playlist: newPlaylist };
                    }
                }
                if (path.startsWith('/api/playlists/')) {
                    const tokenParts = authToken.split('_');
                    const userId = tokenParts[tokenParts.length - 1];
                    const playlistsKey = `playlists_${userId}`;
                    const playlists = JSON.parse(localStorage.getItem(playlistsKey) || '[]');
                    
                    const parts = path.split('/');
                    const playlistId = parseInt(parts[3]);
                    const playlistIndex = playlists.findIndex(p => p.id === playlistId);
                    if (playlistIndex === -1) throw new Error('Playlist not found');
                    
                    if (parts.length === 4 && method === 'GET') {
                        return playlists[playlistIndex];
                    }
                    
                    if (parts.length === 5 && parts[4].split('?')[0] === 'songs' && method === 'POST') {
                        const song = allSongs.find(s => s.id === body.song_id);
                        if (!song) throw new Error('Song not found');
                        
                        const playlist = playlists[playlistIndex];
                        if (playlist.songs.find(s => s.id === song.id)) {
                            throw new Error('Song already in playlist');
                        }
                        
                        playlist.songs.push(song);
                        localStorage.setItem(playlistsKey, JSON.stringify(playlists));
                        return { message: 'Song added to playlist.', playlist };
                    }
                }
                
                throw new Error(`Mock endpoint not implemented: ${method} ${path}`);
            } catch (err) {
                showToast(err.message, true);
                throw err;
            }
        }"""

    # Replace the apiRequest definition in the HTML file
    print("Replacing apiRequest function...")
    html, count = re.subn(api_request_regex, mock_api_request, html)
    print(f"Substitutions made: {count}")
    
    # Save the output standalone HTML file
    output_filename = "music_recommendation_app.html"
    print(f"Writing to {output_filename}...")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Standalone HTML generation completed successfully!")

if __name__ == "__main__":
    main()
