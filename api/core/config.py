"""
Configuration module — loads environment variables and provides settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./cbp_sentry.db"
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    # API
    api_key: str = "demo-key"
    api_version: str = "0.1.0"

    # CORS
    cors_origins: Optional[List[str]] = ["http://localhost:3000"]

    # Services
    senzing_url: Optional[str] = "http://localhost:8250"
    
    # Cloud (cloud-neutral)
    gcp_project: Optional[str] = None
    aws_region: Optional[str] = "us-east-1"

    # Demo mode
    demo_mode: bool = True
    demo_manifest_path: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
