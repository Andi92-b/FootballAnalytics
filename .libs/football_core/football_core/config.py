"""
config.py — reads .env and exposes typed settings.

Usage:
    from football_core.config import settings
    cache_dir = settings.fbref_cache_dir
"""

# Implementation: load .env via python-dotenv; expose FBREF_CACHE_DIR, APP_ENV, LOG_LEVEL
# as a Pydantic BaseSettings model or a simple dataclass.
