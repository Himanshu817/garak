"""Caching utilities for garak."""
from functools import lru_cache
import time
from typing import Any, Dict, Optional

class TimedCache:
    """Cache with TTL support."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp <= self.ttl:
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp."""
        if len(self.cache) >= self.maxsize:
            # Remove oldest item
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        self.cache[key] = (value, time.time())

_result_cache = TimedCache()

def get_cache() -> TimedCache:
    """Get the global result cache instance."""
    return _result_cache