# Application-wide constants

# Supported Genres list for preferences and seeding
GENRES = [
    "Pop",
    "Rock",
    "Hip Hop",
    "Jazz",
    "Classical",
    "Electronic",
    "R&B",
    "Country",
    "Reggae",
    "Metal",
    "Blues",
    "Indie",
    "Latin",
    "Folk"
]

# Recommendation weights
DEFAULT_CONTENT_WEIGHT = 0.5
DEFAULT_COLLABORATIVE_WEIGHT = 0.5

# Standard error messages
ERROR_USER_NOT_FOUND = "User not found."
ERROR_SONG_NOT_FOUND = "Song not found."
ERROR_PLAYLIST_NOT_FOUND = "Playlist not found."
ERROR_UNAUTHORIZED = "Unauthorized access."
ERROR_INVALID_TOKEN = "Token is invalid or expired."
ERROR_MISSING_TOKEN = "Token is missing."
ERROR_EMAIL_EXISTS = "Email already registered."
ERROR_INVALID_RATING = "Rating must be an integer between 1 and 5."
ERROR_GENERIC = "An unexpected error occurred."
