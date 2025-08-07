import json
import time
import logging
from typing import Optional, Dict, Any

class CacheManager:
    """Simple in-memory cache for AI responses and API data"""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _generate_key(self, user_id: int, request_type: str, context: str = "") -> str:
        """Generate cache key based on user, request type, and context"""
        return f"{user_id}:{request_type}:{hash(context)}"
    
    def get(self, user_id: int, request_type: str, context: str = "") -> Optional[Any]:
        """Get cached data if it exists and hasn't expired"""
        key = self._generate_key(user_id, request_type, context)
        
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        
        # Check if expired
        if time.time() > cached_item['expires_at']:
            del self.cache[key]
            return None
        
        logging.debug(f"Cache hit for key: {key}")
        return cached_item['data']
    
    def set(self, user_id: int, request_type: str, data: Any, context: str = "", ttl: Optional[int] = None) -> None:
        """Cache data with expiration"""
        key = self._generate_key(user_id, request_type, context)
        expires_at = time.time() + (ttl or self.default_ttl)
        
        self.cache[key] = {
            'data': data,
            'expires_at': expires_at,
            'created_at': time.time()
        }
        
        logging.debug(f"Cached data for key: {key}")
    
    def invalidate(self, user_id: int, request_type: str = None) -> None:
        """Invalidate cache for a user or specific request type"""
        if request_type:
            # Invalidate specific request type for user
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{user_id}:{request_type}:")]
        else:
            # Invalidate all cache for user
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{user_id}:")]
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logging.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
    
    def cleanup_expired(self) -> None:
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items() 
            if current_time > value['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
cache = CacheManager()