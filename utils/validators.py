import re

def validate_email(email):
    """
    Validates email format using regex.
    """
    if not email:
        return False
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email))

def validate_password(password):
    """
    Validates password strength:
    - Minimum 8 characters.
    - Contains at least one uppercase letter.
    - Contains at least one lowercase letter.
    - Contains at least one number.
    """
    if not password:
        return False
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

def validate_username(username):
    """
    Validates username:
    - Minimum 3 characters, max 50 characters.
    - Alphanumeric, spaces, underscores, or hyphens allowed.
    """
    if not username:
        return False
    if len(username) < 3 or len(username) > 50:
        return False
    username_regex = r'^[\w\s-]+$'
    return bool(re.match(username_regex, username))

def validate_rating(rating):
    """
    Validates rating scale (1-5).
    """
    try:
        r = int(rating)
        return 1 <= r <= 5
    except (ValueError, TypeError):
        return False
