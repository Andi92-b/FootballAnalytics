"""
config.py — reads .env and exposes typed settings.

Usage:
    from football_core.config import settings
    cache_dir = settings.fbref_cache_dir
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class _Settings:
    @property
    def fbref_cache_dir(self) -> Path:
        raw = os.getenv("FBREF_CACHE_DIR", ".cache/fbref")
        return Path(raw)

    @property
    def app_env(self) -> str:
        return os.getenv("APP_ENV", "development")

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")


settings = _Settings()
