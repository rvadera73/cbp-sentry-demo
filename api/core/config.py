"""Configuration management using Pydantic Settings"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Environment
    environment: str = "development"
    debug: bool = True
    demo_mode: bool = True

    # Databases
    database_url: str = "firestore"  # 'firestore' or 'sqlite://...'
    firestore_project: str = "cbp-sentry-demo"
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None

    # APIs
    senzing_url: str = "http://localhost:8250"
    gemini_project: str = "cbp-sentry-demo"
    gemini_model: str = "gemini-1.5-pro"

    # Security
    manifest_password: str = "CBPDemo2026"  # Demo password — use secrets manager in prod
    api_key: Optional[str] = None

    # Senzing
    senzing_sdk_initialized: bool = True
    senzing_db_path: str = "./seed_data/G2C.db"

    # UI
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]

    # Paths
    fixtures_path: str = "./fixtures"
    models_path: str = "./models"
    seed_data_path: str = "./seed_data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()
