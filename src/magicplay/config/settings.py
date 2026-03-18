"""
MagicPlay Configuration Settings

Centralized configuration management using Pydantic settings.
All environment variables are loaded from .env file or system environment.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be configured via:
    1. Environment variables (e.g., DEEPSEEK_API_KEY)
    2. .env file in project root
    3. .env.local file for local overrides (gitignored)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key for LLM services"
    )
    dashscope_api_key: str = Field(
        default="",
        description="DashScope API key for image/video generation"
    )

    # API Endpoints (optional, use defaults if not set)
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API base URL"
    )
    dashscope_base_url: Optional[str] = Field(
        default=None,
        description="DashScope API base URL (uses SDK default if not set)"
    )

    # Model Configuration
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek model to use"
    )
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for LLM generation"
    )

    # Generation Settings
    max_retry_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for API calls"
    )
    default_video_duration: int = Field(
        default=8,
        ge=1,
        le=60,
        description="Default video duration in seconds"
    )
    min_video_duration: int = Field(
        default=2,
        ge=1,
        description="Minimum video duration in seconds"
    )
    max_video_duration: int = Field(
        default=15,
        ge=1,
        description="Maximum video duration in seconds"
    )

    # Quality Settings
    default_quality_threshold: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Default quality threshold for generated content"
    )
    enable_quality_check: bool = Field(
        default=True,
        description="Enable quality evaluation for generated content"
    )

    # Caching Settings
    enable_caching: bool = Field(
        default=True,
        description="Enable resource caching"
    )
    cache_max_age_days: int = Field(
        default=30,
        ge=1,
        description="Maximum age of cached resources in days"
    )

    # Parallel Processing
    max_parallel_tasks: int = Field(
        default=3,
        ge=1,
        description="Maximum number of parallel tasks"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file (None for console only)"
    )

    # Experiment Tracking
    enable_experiments: bool = Field(
        default=False,
        description="Enable experiment tracking"
    )

    # Project Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent,
        description="Project root directory"
    )

    @field_validator("deepseek_api_key")
    @classmethod
    def validate_deepseek_key(cls, v: str) -> str:
        """Validate DeepSeek API key is provided."""
        if not v:
            raise ValueError(
                "DEEPSEEK_API_KEY environment variable is required. "
                "Please set it in your .env file or system environment."
            )
        return v

    @field_validator("dashscope_api_key")
    @classmethod
    def validate_dashscope_key(cls, v: str) -> str:
        """Warn if DashScope API key is not provided."""
        if not v:
            import warnings
            warnings.warn(
                "DASHSCOPE_API_KEY environment variable is not set. "
                "Image and video generation will fail."
            )
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        import os
        return os.getenv("MAGICPLAY_ENV", "development") == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return not self.is_production


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only load settings once,
    even if this function is called multiple times.

    Returns:
        Settings: Application settings instance
    """
    # Load environment variables from .env files
    load_dotenv()
    load_dotenv(".env.local", override=True)

    return Settings()
