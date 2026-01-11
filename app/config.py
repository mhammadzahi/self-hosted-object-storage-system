"""
Configuration management using Pydantic settings.
Environment variables are loaded from .env file or system environment.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    app_name: str = "Object Storage API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Storage Configuration
    storage_backend: str = "local"  # Future: s3, minio, gcs
    storage_base_path: str = "UPLOAD_DIR"
    max_file_size: int = 5 * 1024 * 1024 * 1024  # 5GB default
    
    # Security
    allowed_origins: list[str] = ["*"]
    enable_path_traversal_protection: bool = True
    
    # Performance
    chunk_size: int = 1024 * 1024  # 1MB chunks for streaming
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_storage_path(self) -> Path:
        """Get the resolved storage base path."""
        return Path(self.storage_base_path).resolve()


# Global settings instance
settings = Settings()

# Ensure storage directory exists
settings.get_storage_path().mkdir(parents=True, exist_ok=True)
