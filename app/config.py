"""
Configuration module.
Loads environment variables and provides app-wide settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    OWNER_IDS: list[int] = [
        int(uid.strip())
        for uid in os.getenv("OWNER_IDS", "").split(",")
        if uid.strip().isdigit()
    ]
    DB_PATH: str = os.getenv("DB_PATH", "bot_database.db")
    MASTER_KEY: str = os.getenv("MASTER_KEY", "")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration. Returns list of errors."""
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN tidak ditemukan di .env")
        if not cls.OWNER_IDS:
            errors.append("OWNER_IDS tidak ditemukan di .env")
        if not cls.MASTER_KEY:
            errors.append("MASTER_KEY tidak ditemukan di .env")
        return errors
