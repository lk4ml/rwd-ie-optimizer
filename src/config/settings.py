"""
Configuration settings for RWD IE Optimizer.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL_DEFAULT: str = os.getenv("MODEL_DEFAULT", "gpt-4o")
    MODEL_RESEARCH: str = os.getenv("MODEL_RESEARCH", "gpt-4-turbo")
    MODEL_CODING: str = os.getenv("MODEL_CODING", "gpt-4o")

    # Database Configuration
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/rwd_claims.db")

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/rwd_ie_optimizer.log")

    # System Settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    QUERY_TIMEOUT_SECONDS: int = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))

    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return True

    @classmethod
    def get_prompts_dir(cls) -> Path:
        """Get path to prompts directory."""
        return Path(__file__).parent / "prompts"


# Singleton instance
settings = Settings()
