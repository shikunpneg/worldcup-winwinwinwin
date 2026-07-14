"""
Utility functions for data collection.
"""

import os
import time
import json
from datetime import datetime
from typing import Optional


class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl: int = 60):
        self._cache = {}
        self._timestamps = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[any]:
        if key in self._cache:
            elapsed = time.time() - self._timestamps[key]
            if elapsed < self.ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key: str, value: any):
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self):
        self._cache.clear()
        self._timestamps.clear()


def ensure_dir(path: str):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def safe_int(value, default=0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_datetime(dt_str: str) -> Optional[str]:
    """Parse datetime string to ISO format."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except (ValueError, AttributeError):
        return dt_str
