from models import db
from models.song import Song
from utils.constants import GENRES
import random

class SongService:
    @staticmethod
    def get_songs(limit=20, offset=0):
        songs = Song.query.filter(Song.youtube_id != None, Song.youtube_id != '').limit(limit).offset(offset).all()
        return [s.to_dict() for s in songs]

    @staticmethod
    def get_song_by_id(song_id):
        song = Song.query.get(song_id)
        if not song:
            return None
        return song.to_dict()

    @staticmethod
    def search_songs(query, limit=20):
        if not query:
            return []
            
        import urllib.request
        import urllib.parse
        import json
        import re
        
        # Define keywords for generic query classification and robust filtering
        generic_keywords = {
            'telugu', 'telug', 'tamil', 'tami', 'hindi', 'hind', 'malayalam', 'kannada', 'punjabi', 
            'bhojpuri', 'bengali', 'marathi', 'gujarati', 'english', 'spanish', 'french', 'korean', 'japanese',
            'pop', 'rock', 'jazz', 'classical', 'electronic', 'edm', 'hiphop', 'hip hop',
            'rap', 'r&b', 'indie', 'country', 'latin', 'devotional', 'bhajans', 'bhajan',
            'ghazal', 'qawwali', 'folk', 'melody', 'melodies', 'hits', 'classics', 'oldies'
        }
        stop_words = {
            'song', 'songs', 'music', 'latest', 'new', 'old', 'best', 'top', 'love', 'sad', 
            'happy', 'hit', 'hits', 'video', 'audio', 'track', 'tracks', 'playlist'
        }
        
        # Check if query is generic
        words = re.findall(r'\b\w+\b', query.lower())
        is_generic = False
        if words:
            is_generic = all(w in generic_keywords or w in stop_words for w in words)
            
        exclude_keywords = [
            'trailer', 'teaser', 'full movie', 'episode', 'promo', 'serial', 'interview', 
            'review', 'reaction', 'press meet', 'success meet', 'behind the scenes', 
            'making of', 'press conference', 'gossip', 'news', 'anchor speech', 'speech',
            'event live', 'pre-release', 'audio launch', 'vlog', 'daily vlog', 'spoiler',
            'roast', 'debate', 'comedy scene', 'short film', 'full episode', 'web series',
            'show', 'skit', 'performance', 'season', 'grand finale', 'finale', 'judges', 
            'contestant', 'contestants', 'elimination', 'audition', 'auditions', 'tv show', 
            'television', 'etv', 'zee', 'gemini tv', 'star maa', 'sun tv', 'star vijay', 
            'colors', 'sony', 'sab tv', 'explained', 'details', 'update', 'updates', 
            'rumor', 'rumours', 'analysis', 'discussion', 'scene', 'scenes', 'climax', 
            'comedy', 'fight'
        ]
        
        song_indicators = [
            'song', 'songs', 'lyric', 'lyrics', 'video', 'audio', 'music', 'bgm', 'soundtrack', 
            'theme', 'singles', 'singing', 'sing', 'melody', 'hits', 'karaoke', 'remix', 'mashup', 
            'cover', 'unplugged', 'acoustic'
        ]
        
        # 1. Search local DB first
        search_pattern = f"%{query}%"
        local_songs = Song.query.filter(
            (Song.title.like(search_pattern)) | 
            (Song.artist.like(search_pattern)) | 
            (Song.album.like(search_pattern)) |
            (Song.genre.like(search_pattern))
        ).filter(Song.youtube_id != None, Song.youtube_id != '').limit(limit).all()
        
        # Filter local DB results to ensure they conform to filters
        local_results = []
        for s in local_songs:
            title_lower = s.title.lower()
            if any(kw in title_lower for kw in exclude_keywords):
                continue
            # Duration bounds (1 min to 10 mins) enforced on scraped search tracks
            if s.album == "YouTube Search" and (s.duration < 60 or s.duration > 600):
                continue
            # Song indicators check on scraped search tracks if query is generic
            if is_generic and s.album == "YouTube Search":
                if not any(ind in title_lower for ind in song_indicators):
                    continue
            local_results.append(s.to_dict())
            
        local_youtube_ids = {s['youtube_id'] for s in local_results if s.get('youtube_id')}

        # 2. Scrape YouTube search to fetch new matching videos
        yt_results = []
        try:
            # Refine query: if it doesn't contain common music identifiers, append " song"
            refined_query = query
            lower_query = query.lower()
            music_keywords = ['song', 'songs', 'music', 'audio', 'lyric', 'lyrics', 'video', 'album', 'playlist', 'singer', 'track', 'tracks', 'theme', 'soundtrack', 'bgm']
            if not any(kw in lower_query for kw in music_keywords):
                refined_query = f"{query} song"

            search_query = urllib.parse.quote(refined_query)
            url = f"https://www.youtube.com/results?search_query={search_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
                
                # Find start of ytInitialData
                start_idx = html.find("ytInitialData = ")
                if start_idx != -1:
                    json_start = html.find("{", start_idx)
                    if json_start != -1:
                        # Parse JSON by brace-tracking
                        brace_count = 0
                        json_end = -1
                        in_string = False
                        escape = False
                        for i in range(json_start, len(html)):
                            char = html[i]
                            if escape:
                                escape = False
                                continue
                            if char == '\\':
                                escape = True
                                continue
                            if char == '"':
                                in_string = not in_string
                                continue
                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = i + 1
                                        break
                        if json_end != -1:
                            json_str = html[json_start:json_end]
                            data = json.loads(json_str)
                            
                            # Navigate contents
                            section_list = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                            
                            for section in section_list:
                                item_section = section.get('itemSectionRenderer', {})
                                for item in item_section.get('contents', []):
                                    if 'videoRenderer' in item:
                                        vr = item['videoRenderer']
                                        
                                        video_id = vr.get('videoId')
                                        if not video_id:
                                            continue
                                            
                                        # Extract title
                                        title_runs = vr.get('title', {}).get('runs', [])
                                        yt_title = "".join([run.get('text', '') for run in title_runs]) if title_runs else ""
                                        if not yt_title:
                                            continue
                                            
                                        # Filter out non-song videos (trailers, episodes, interviews, promos, reviews, etc.)
                                        yt_title_lower = yt_title.lower()
                                        if any(kw in yt_title_lower for kw in exclude_keywords):
                                            continue
                                        
                                        # Extract channel name
                                        channel_runs = vr.get('ownerText', {}).get('runs', [])
                                        channel = channel_runs[0].get('text', '') if channel_runs else ""
                                        
                                        # Extract duration
                                        duration_text = vr.get('lengthText', {}).get('simpleText', '')
                                        duration_sec = 180 # default fallback
                                        if duration_text:
                                            parts = duration_text.split(':')
                                            try:
                                                if len(parts) == 2: # MM:SS
                                                    duration_sec = int(parts[0]) * 60 + int(parts[1])
                                                elif len(parts) == 3: # HH:MM:SS
                                                    duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                            except ValueError:
                                                pass
                                        
                                        # Filter out videos that are too short (likely shorts/teasers) or too long (likely full movie compilations/jukeboxes)
                                        # Restricting duration to [60 seconds, 10 minutes (600 seconds)]
                                        if duration_sec < 60 or duration_sec > 600:
                                            continue
                                            
                                        # Enforce song indicators check for generic queries
                                        if is_generic:
                                            if not any(ind in yt_title_lower for ind in song_indicators):
                                                continue
                                                
                                        yt_results.append({
                                            'youtube_id': video_id,
                                            'yt_title': yt_title,
                                            'channel': channel,
                                            'duration': duration_sec
                                        })
                                        if len(yt_results) >= 8: # scrape up to 8 top matches
                                            break
                                if len(yt_results) >= 8:
                                    break
        except Exception as e:
            print(f"Error scraping YouTube during search: {e}")

        # 3. Clean and process scraped results, adding new ones to local DB
        combined_results = list(local_results)
        
        for item in yt_results:
            yt_id = item['youtube_id']
            # If already returned in local results, skip inserting
            if yt_id in local_youtube_ids:
                continue
                
            # Check if this youtube_id is already in DB but wasn't caught by the text query
            existing_song = Song.query.filter_by(youtube_id=yt_id).first()
            if existing_song:
                combined_results.append(existing_song.to_dict())
                local_youtube_ids.add(yt_id)
                continue
                
            # Parse artist/title from YouTube
            delimiters = [' - ', ' – ', ' — ', ' | ', ' : ']
            artist = item['channel']
            title = item['yt_title']
            
            for delim in delimiters:
                if delim in item['yt_title']:
                    parts = item['yt_title'].split(delim, 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                    break
                    
            # Clean common bracket suffixes
            clean_patterns = [
                r'\s*[\(\[][Oo]fficial\s+[Mm]usic\s+[Vv]ideo[\)\]]',
                r'\s*[\(\[][Oo]fficial\s+[Vv]ideo[\)\]]',
                r'\s*[\(\[][Oo]fficial\s+[Aa]udio[\)\]]',
                r'\s*[\(\[][Oo]fficial\s+[Ll]yric\s+[Vv]ideo[\)\]]',
                r'\s*[\(\[][Oo]fficial[\)\]]',
                r'\s*[\(\[][Ll]yrics[\)\]]',
                r'\s*[\(\[][Ll]yric[\)\]]',
                r'\s*[\(\[][Vv]ideo[\)\]]',
                r'\s*[\(\[][Aa]udio[\)\]]',
                r'\s*[\(\[][H]D[\)\]]',
                r'\s*[\(\[][4]K[\)\]]',
            ]
            for pattern in clean_patterns:
                title = re.sub(pattern, '', title)
                artist = re.sub(pattern, '', artist)
                
            title = title.strip()
            artist = artist.strip()
            artist = re.sub(r'\s*-\s*Topic$', '', artist)
            
            # Create dynamic DB song entry
            try:
                new_song = Song(
                    title=title or item['yt_title'],
                    artist=artist or item['channel'] or "Unknown Artist",
                    album="YouTube Search",
                    genre="General",
                    duration=item['duration'],
                    youtube_id=yt_id,
                    tempo=random.uniform(80.0, 140.0),
                    energy=random.uniform(0.3, 0.8),
                    danceability=random.uniform(0.3, 0.8),
                    valence=random.uniform(0.3, 0.8),
                    acousticness=random.uniform(0.1, 0.7),
                    popularity=50.0
                )
                db.session.add(new_song)
                db.session.commit()
                combined_results.append(new_song.to_dict())
                local_youtube_ids.add(yt_id)
            except Exception as ex:
                db.session.rollback()
                print(f"Error saving dynamic YouTube song to DB: {ex}")
                
        return combined_results[:limit]

    @staticmethod
    def get_genres():
        # Query distinct genres from DB and union with constant GENRES
        db_genres = db.session.query(Song.genre).distinct().all()
        result = set(GENRES)
        for g in db_genres:
            if g[0]:
                result.add(g[0])
        return sorted(list(result))

    @staticmethod
    def seed_default_songs():
        """
        Seeds 50+ diverse mock songs with descriptive audio features
        to ensure content-based and collaborative recommendations are immediately testable.
        """
        if Song.query.count() > 0:
            return False # Seeding not needed
            
        # Defining 50 mock songs across genres with specific audio profile signatures
        mock_songs = [
            # Pop (High energy, high danceability, high valence)
            {"title": "Blinding Lights", "artist": "The Weeknd", "album": "After Hours", "genre": "Pop", "duration": 200, "tempo": 171.0, "energy": 0.8, "danceability": 0.75, "valence": 0.65, "acousticness": 0.1, "popularity": 95.0},
            {"title": "As It Was", "artist": "Harry Styles", "album": "Harry's House", "genre": "Pop", "duration": 167, "tempo": 174.0, "energy": 0.73, "danceability": 0.52, "valence": 0.66, "acousticness": 0.34, "popularity": 92.0},
            {"title": "Levitating", "artist": "Dua Lipa", "album": "Future Nostalgia", "genre": "Pop", "duration": 203, "tempo": 103.0, "energy": 0.82, "danceability": 0.90, "valence": 0.91, "acousticness": 0.02, "popularity": 89.0},
            {"title": "Stay", "artist": "The Kid LAROI & Justin Bieber", "album": "F*CK LOVE 3", "genre": "Pop", "duration": 141, "tempo": 170.0, "energy": 0.76, "danceability": 0.59, "valence": 0.48, "acousticness": 0.04, "popularity": 88.0},
            {"title": "Bad Habits", "artist": "Ed Sheeran", "album": "=", "genre": "Pop", "duration": 231, "tempo": 126.0, "energy": 0.89, "danceability": 0.80, "valence": 0.59, "acousticness": 0.05, "popularity": 87.0},
            
            # Rock (High energy, low acousticness, mid-range danceability)
            {"title": "Bohemian Rhapsody", "artist": "Queen", "album": "A Night at the Opera", "genre": "Rock", "duration": 354, "tempo": 143.0, "energy": 0.40, "danceability": 0.39, "valence": 0.22, "acousticness": 0.27, "popularity": 91.0},
            {"title": "Smells Like Teen Spirit", "artist": "Nirvana", "album": "Nevermind", "genre": "Rock", "duration": 301, "tempo": 117.0, "energy": 0.91, "danceability": 0.50, "valence": 0.72, "acousticness": 0.00, "popularity": 90.0},
            {"title": "Hotel California", "artist": "Eagles", "album": "Hotel California", "genre": "Rock", "duration": 391, "tempo": 147.0, "energy": 0.52, "danceability": 0.58, "valence": 0.40, "acousticness": 0.01, "popularity": 89.0},
            {"title": "Stairway to Heaven", "artist": "Led Zeppelin", "album": "Led Zeppelin IV", "genre": "Rock", "duration": 482, "tempo": 82.0, "energy": 0.34, "danceability": 0.30, "valence": 0.19, "acousticness": 0.58, "popularity": 86.0},
            {"title": "Sweet Child O' Mine", "artist": "Guns N' Roses", "album": "Appetite for Destruction", "genre": "Rock", "duration": 356, "tempo": 125.0, "energy": 0.90, "danceability": 0.45, "valence": 0.62, "acousticness": 0.09, "popularity": 87.0},
            
            # Hip Hop (High danceability, mid-high energy, low acousticness, strong tempo)
            {"title": "Lose Yourself", "artist": "Eminem", "album": "8 Mile", "genre": "Hip Hop", "duration": 326, "tempo": 171.0, "energy": 0.74, "danceability": 0.69, "valence": 0.06, "acousticness": 0.01, "popularity": 90.0},
            {"title": "SICKO MODE", "artist": "Travis Scott", "album": "ASTROWORLD", "genre": "Hip Hop", "duration": 312, "tempo": 155.0, "energy": 0.73, "danceability": 0.83, "valence": 0.45, "acousticness": 0.01, "popularity": 88.0},
            {"title": "HUMBLE.", "artist": "Kendrick Lamar", "album": "DAMN.", "genre": "Hip Hop", "duration": 177, "tempo": 150.0, "energy": 0.81, "danceability": 0.91, "valence": 0.42, "acousticness": 0.00, "popularity": 89.0},
            {"title": "God's Plan", "artist": "Drake", "album": "Scorpion", "genre": "Hip Hop", "duration": 198, "tempo": 77.0, "energy": 0.45, "danceability": 0.75, "valence": 0.36, "acousticness": 0.03, "popularity": 87.0},
            {"title": "Industry Baby", "artist": "Lil Nas X & Jack Harlow", "album": "Montero", "genre": "Hip Hop", "duration": 212, "tempo": 150.0, "energy": 0.70, "danceability": 0.74, "valence": 0.89, "acousticness": 0.02, "popularity": 85.0},
            
            # Electronic (Very high tempo/energy, high danceability, very low acousticness)
            {"title": "Wake Me Up", "artist": "Avicii", "album": "True", "genre": "Electronic", "duration": 247, "tempo": 124.0, "energy": 0.78, "danceability": 0.53, "valence": 0.64, "acousticness": 0.00, "popularity": 87.0},
            {"title": "Clarity", "artist": "Zedd", "album": "Clarity", "genre": "Electronic", "duration": 271, "tempo": 128.0, "energy": 0.78, "danceability": 0.61, "valence": 0.38, "acousticness": 0.04, "popularity": 82.0},
            {"title": "Titanium", "artist": "David Guetta & Sia", "album": "Nothing but the Beat", "genre": "Electronic", "duration": 245, "tempo": 126.0, "energy": 0.79, "danceability": 0.60, "valence": 0.30, "acousticness": 0.01, "popularity": 84.0},
            {"title": "Scary Monsters and Nice Sprites", "artist": "Skrillex", "album": "Scary Monsters and Nice Sprites", "genre": "Electronic", "duration": 243, "tempo": 140.0, "energy": 0.95, "danceability": 0.64, "valence": 0.39, "acousticness": 0.01, "popularity": 75.0},
            {"title": "Strobe", "artist": "deadmau5", "album": "For Lack of a Better Name", "genre": "Electronic", "duration": 637, "tempo": 128.0, "energy": 0.68, "danceability": 0.59, "valence": 0.11, "acousticness": 0.00, "popularity": 72.0},
            
            # R&B (Mid tempo, mid-high danceability, low-mid acousticness, emotional valence)
            {"title": "Superstition", "artist": "Stevie Wonder", "album": "Talking Book", "genre": "R&B", "duration": 266, "tempo": 100.0, "energy": 0.66, "danceability": 0.81, "valence": 0.96, "acousticness": 0.09, "popularity": 83.0},
            {"title": "Adorn", "artist": "Miguel", "album": "Kaleidoscope Dream", "genre": "R&B", "duration": 193, "tempo": 90.0, "energy": 0.55, "danceability": 0.68, "valence": 0.49, "acousticness": 0.12, "popularity": 78.0},
            {"title": "Redbone", "artist": "Childish Gambino", "album": '"Awaken, My Love!"', "genre": "R&B", "duration": 326, "tempo": 160.0, "energy": 0.36, "danceability": 0.74, "valence": 0.59, "acousticness": 0.17, "popularity": 87.0},
            {"title": "We Belong Together", "artist": "Mariah Carey", "album": "The Emancipation of Mimi", "genre": "R&B", "duration": 201, "tempo": 80.0, "energy": 0.44, "danceability": 0.83, "valence": 0.76, "acousticness": 0.03, "popularity": 81.0},
            {"title": "No Guidance", "artist": "Chris Brown & Drake", "album": "Indigo", "genre": "R&B", "duration": 260, "tempo": 93.0, "energy": 0.45, "danceability": 0.70, "valence": 0.14, "acousticness": 0.12, "popularity": 83.0},

            # Jazz (Mid-low tempo, high acousticness, low-mid energy, complex valence)
            {"title": "Take Five", "artist": "Dave Brubeck", "album": "Time Out", "genre": "Jazz", "duration": 324, "tempo": 174.0, "energy": 0.25, "danceability": 0.45, "valence": 0.51, "acousticness": 0.82, "popularity": 79.0},
            {"title": "So What", "artist": "Miles Davis", "album": "Kind of Blue", "genre": "Jazz", "duration": 562, "tempo": 135.0, "energy": 0.15, "danceability": 0.50, "valence": 0.33, "acousticness": 0.90, "popularity": 78.0},
            {"title": "My Favorite Things", "artist": "John Coltrane", "album": "My Favorite Things", "genre": "Jazz", "duration": 821, "tempo": 120.0, "energy": 0.35, "danceability": 0.38, "valence": 0.40, "acousticness": 0.75, "popularity": 73.0},
            {"title": "Come Fly With Me", "artist": "Frank Sinatra", "album": "Come Fly with Me", "genre": "Jazz", "duration": 199, "tempo": 133.0, "energy": 0.53, "danceability": 0.52, "valence": 0.65, "acousticness": 0.67, "popularity": 80.0},
            {"title": "Don't Know Why", "artist": "Norah Jones", "album": "Come Away with Me", "genre": "Jazz", "duration": 186, "tempo": 88.0, "energy": 0.20, "danceability": 0.73, "valence": 0.62, "acousticness": 0.88, "popularity": 83.0},

            # Classical (Very low energy, very high acousticness, low danceability, variable tempo)
            {"title": "Symphony No. 5 in C minor", "artist": "Ludwig van Beethoven", "album": "Beethoven: Symphonies Nos. 5 & 7", "genre": "Classical", "duration": 482, "tempo": 108.0, "energy": 0.22, "danceability": 0.29, "valence": 0.31, "acousticness": 0.91, "popularity": 76.0},
            {"title": "Clair de Lune", "artist": "Claude Debussy", "album": "Suite bergamasque", "genre": "Classical", "duration": 305, "tempo": 60.0, "energy": 0.05, "danceability": 0.33, "valence": 0.12, "acousticness": 0.99, "popularity": 81.0},
            {"title": "Nocturne in E-flat major", "artist": "Frédéric Chopin", "album": "Chopin: Nocturnes", "genre": "Classical", "duration": 270, "tempo": 64.0, "energy": 0.02, "danceability": 0.38, "valence": 0.08, "acousticness": 0.99, "popularity": 82.0},
            {"title": "Canon in D major", "artist": "Johann Pachelbel", "album": "Pachelbel's Greatest Hits", "genre": "Classical", "duration": 380, "tempo": 80.0, "energy": 0.12, "danceability": 0.25, "valence": 0.45, "acousticness": 0.95, "popularity": 79.0},
            {"title": "The Four Seasons: Spring", "artist": "Antonio Vivaldi", "album": "The Four Seasons", "genre": "Classical", "duration": 215, "tempo": 115.0, "energy": 0.35, "danceability": 0.42, "valence": 0.81, "acousticness": 0.85, "popularity": 78.0},

            # Country (Mid energy, high valence, mid-high acousticness, acoustic instruments)
            {"title": "Tennessee Whiskey", "artist": "Chris Stapleton", "album": "Traveller", "genre": "Country", "duration": 293, "tempo": 75.0, "energy": 0.43, "danceability": 0.39, "valence": 0.51, "acousticness": 0.56, "popularity": 88.0},
            {"title": "Jolene", "artist": "Dolly Parton", "album": "Jolene", "genre": "Country", "duration": 161, "tempo": 110.0, "energy": 0.55, "danceability": 0.67, "valence": 0.80, "acousticness": 0.41, "popularity": 82.0},
            {"title": "Take Me Home, Country Roads", "artist": "John Denver", "album": "Poems, Prayers & Promises", "genre": "Country", "duration": 190, "tempo": 91.0, "energy": 0.52, "danceability": 0.62, "valence": 0.74, "acousticness": 0.48, "popularity": 86.0},
            {"title": "Whiskey Glasses", "artist": "Morgan Wallen", "album": "If I Know Me", "genre": "Country", "duration": 234, "tempo": 150.0, "energy": 0.70, "danceability": 0.61, "valence": 0.71, "acousticness": 0.36, "popularity": 85.0},
            {"title": "Man! I Feel Like a Woman!", "artist": "Shania Twain", "album": "Come On Over", "genre": "Country", "duration": 234, "tempo": 125.0, "energy": 0.86, "danceability": 0.66, "valence": 0.69, "acousticness": 0.12, "popularity": 81.0},
            
            # Indie (Mid-high energy, high acousticness/valence, unique signatures)
            {"title": "Riptide", "artist": "Vance Joy", "album": "Dream Your Life Away", "genre": "Indie", "duration": 204, "tempo": 125.0, "energy": 0.73, "danceability": 0.48, "valence": 0.51, "acousticness": 0.73, "popularity": 86.0},
            {"title": "Ho Hey", "artist": "The Lumineers", "album": "The Lumineers", "genre": "Indie", "duration": 163, "tempo": 80.0, "energy": 0.49, "danceability": 0.69, "valence": 0.44, "acousticness": 0.79, "popularity": 83.0},
            {"title": "Dog Days Are Over", "artist": "Florence + The Machine", "album": "Lungs", "genre": "Indie", "duration": 252, "tempo": 150.0, "energy": 0.80, "danceability": 0.51, "valence": 0.78, "acousticness": 0.08, "popularity": 81.0},
            {"title": "Little Talks", "artist": "Of Monsters and Men", "album": "My Head Is an Animal", "genre": "Indie", "duration": 266, "tempo": 103.0, "energy": 0.79, "danceability": 0.43, "valence": 0.56, "acousticness": 0.02, "popularity": 82.0},
            {"title": "Skinny Love", "artist": "Bon Iver", "album": "For Emma, Forever Ago", "genre": "Indie", "duration": 239, "tempo": 77.0, "energy": 0.31, "danceability": 0.55, "valence": 0.22, "acousticness": 0.85, "popularity": 79.0},

            # Latin (Very high danceability, high energy, low-mid acousticness)
            {"title": "Despacito", "artist": "Luis Fonsi & Daddy Yankee", "album": "Vida", "genre": "Latin", "duration": 228, "tempo": 89.0, "energy": 0.78, "danceability": 0.66, "valence": 0.82, "acousticness": 0.20, "popularity": 89.0},
            {"title": "Dákiti", "artist": "Bad Bunny & Jhay Cortez", "album": "El Último Tour Del Mundo", "genre": "Latin", "duration": 205, "tempo": 110.0, "energy": 0.57, "danceability": 0.73, "valence": 0.50, "acousticness": 0.40, "popularity": 86.0},
            {"title": "Mi Gente", "artist": "J Balvin & Willy William", "album": "Vibras", "genre": "Latin", "duration": 189, "tempo": 105.0, "energy": 0.72, "danceability": 0.76, "valence": 0.61, "acousticness": 0.02, "popularity": 83.0},
            {"title": "Chantaje", "artist": "Shakira & Maluma", "album": "El Dorado", "genre": "Latin", "duration": 195, "tempo": 102.0, "energy": 0.77, "danceability": 0.85, "valence": 0.91, "acousticness": 0.19, "popularity": 82.0},
            {"title": "Havana", "artist": "Camila Cabello & Young Thug", "album": "Camila", "genre": "Latin", "duration": 217, "tempo": 105.0, "energy": 0.52, "danceability": 0.77, "valence": 0.39, "acousticness": 0.18, "popularity": 85.0}
        ]
        
        for i, data in enumerate(mock_songs):
            if 'youtube_id' not in data:
                data['youtube_id'] = f"mock_yt_id_{i}"
            song = Song(**data)
            db.session.add(song)
            
        db.session.commit()
        return True

    @staticmethod
    def get_youtube_id(song_id, blacklist=None):
        song = Song.query.get(song_id)
        if not song:
            return None
            
        blacklisted_ids = set()
        if blacklist:
            if isinstance(blacklist, str):
                blacklisted_ids.update(x.strip() for x in blacklist.split(',') if x.strip())
            else:
                blacklisted_ids.update(blacklist)
                
        if song.youtube_id and song.youtube_id not in blacklisted_ids:
            return song.youtube_id
            
        # Search YouTube using a clean scrape approach
        import urllib.request
        import urllib.parse
        import re
        
        query = f"{song.title} {song.artist} lyric video"
        try:
            search_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={search_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
                # Find video IDs
                video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
                if video_ids:
                    new_yt_id = None
                    for vid in video_ids:
                        if vid not in blacklisted_ids:
                            new_yt_id = vid
                            break
                    if new_yt_id:
                        song.youtube_id = new_yt_id
                        db.session.commit()
                        return new_yt_id
        except Exception as e:
            print(f"Error searching YouTube for '{query}': {e}")
            
        return None

    @staticmethod
    def delete_song(song_id):
        song = Song.query.get(song_id)
        if not song:
            return False
        db.session.delete(song)
        db.session.commit()
        return True


