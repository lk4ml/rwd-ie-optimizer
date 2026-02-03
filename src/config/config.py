"""
Application Configuration
Centralized settings management
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    """Database configuration"""
    path: str = "data/rwd_claims.db"

    @property
    def full_path(self) -> Path:
        return Path(__file__).parent.parent.parent / self.path


class AIConfig(BaseModel):
    """AI/LLM configuration"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Model settings
    default_model: str = "gpt-4o"
    research_model: str = "gpt-4-turbo"
    coding_model: str = "gpt-4o"
    claude_model: str = "claude-sonnet-4-20250514"

    # Limits
    max_tokens: int = 2000
    query_timeout: int = 30


class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    # CORS
    cors_origins: list = ["*"]


class AppConfig(BaseModel):
    """Main application configuration"""
    env: str = "development"
    debug: bool = False
    version: str = "2.0.0"

    database: DatabaseConfig = DatabaseConfig()
    ai: AIConfig = AIConfig()
    server: ServerConfig = ServerConfig()


def load_config() -> AppConfig:
    """Load configuration from environment variables"""

    # Database
    db_config = DatabaseConfig(
        path=os.getenv("DATABASE_PATH", "data/rwd_claims.db")
    )

    # AI
    ai_config = AIConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        default_model=os.getenv("MODEL_DEFAULT", "gpt-4o"),
        research_model=os.getenv("MODEL_RESEARCH", "gpt-4-turbo"),
        coding_model=os.getenv("MODEL_CODING", "gpt-4o"),
        max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
        query_timeout=int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))
    )

    # Server
    server_config = ServerConfig(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

    # App
    config = AppConfig(
        env=os.getenv("ENV", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        database=db_config,
        ai=ai_config,
        server=server_config
    )

    return config


# Global config instance
config = load_config()
