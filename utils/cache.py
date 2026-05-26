import time

class SimpleCache:
    """
    An in-memory dictionary-based caching mechanism.
    Supports TTL expiration and pattern-based key deletion.
    """
    def __init__(self):
        self._cache = {}

    def get(self, key):
        if key not in self._cache:
            return None
        
        value, expires_at = self._cache[key]
        if expires_at and time.time() > expires_at:
            # Entry expired
            del self._cache[key]
            return None
            
        return value

    def set(self, key, value, timeout=300):
        """
        Set value in cache. timeout is in seconds.
        """
        expires_at = time.time() + timeout if timeout else None
        self._cache[key] = (value, expires_at)
        return True

    def delete(self, key):
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        self._cache.clear()
        return True

    def delete_pattern(self, pattern):
        """
        Deletes all keys starting with pattern.
        """
        keys_to_delete = [k for k in self._cache.keys() if str(k).startswith(pattern)]
        for k in keys_to_delete:
            del self._cache[k]
        return len(keys_to_delete)

# Global cache instance
cache = SimpleCache()
