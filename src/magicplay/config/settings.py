"""
MagicPlay Configuration Settings

Centralized configuration management using Pydantic settings.

Configuration sources (in order of precedence):
1. config.yaml - User-friendly YAML configuration file
2. Environment variables (e.g., DEEPSEEK_API_KEY)
3. .env file in project root
4. .env.local file for local overrides (gitignored)

For sensitive values (API keys), use environment variables or .env file.
For non-sensitive settings, use config.yaml.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml file.

    Returns:
        Dictionary with configuration values
    """
    config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    if config_path.exists():
        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # PyYAML not installed, skip config.yaml
            return {}
    return {}


class Settings(BaseSettings):
    """
    Application settings loaded from multiple sources.

    Configuration sources (in order of precedence):
    1. Environment variables (highest priority)
    2. config.yaml file
    3. .env file
    4. Default values (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys (from environment variables only - never put in config.yaml)
    deepseek_api_key: str = Field(
        default="", description="DeepSeek API key for LLM services"
    )
    dashscope_api_key: str = Field(
        default="", description="DashScope API key for image/video generation"
    )

    # API Endpoints
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", description="DeepSeek API base URL"
    )
    dashscope_base_url: Optional[str] = Field(
        default=None, description="DashScope API base URL (uses SDK default if not set)"
    )

    # Jimeng (即梦) API Configuration
    jimeng_access_key: str = Field(
        default="", description="Jimeng AI Access Key (Volcengine)"
    )
    jimeng_secret_key: str = Field(
        default="", description="Jimeng AI Secret Key (Volcengine)"
    )
    jimeng_api_base_url: str = Field(
        default="https://visual.volcengineapi.com", description="Jimeng API base URL"
    )
    jimeng_default_aspect_ratio: str = Field(
        default="16:9", description="Default Jimeng video aspect ratio"
    )

    # Model Configuration
    deepseek_model: str = Field(
        default="deepseek-chat", description="DeepSeek model to use"
    )

    # Provider Configuration
    default_video_provider: str = Field(
        default="qwen", description="Default video generation provider (qwen or jimeng)"
    )
    default_image_provider: str = Field(
        default="qwen", description="Default image generation provider (qwen or jimeng)"
    )
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for LLM generation",
    )

    # Generation Settings
    max_retry_attempts: int = Field(
        default=3, ge=1, description="Maximum retry attempts for API calls"
    )
    default_video_duration: int = Field(
        default=8, ge=1, le=60, description="Default video duration in seconds"
    )
    min_video_duration: int = Field(
        default=2, ge=1, description="Minimum video duration in seconds"
    )
    max_video_duration: int = Field(
        default=15, ge=1, description="Maximum video duration in seconds"
    )

    # Quality Settings
    default_quality_threshold: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Default quality threshold for generated content",
    )
    enable_quality_check: bool = Field(
        default=True, description="Enable quality evaluation for generated content"
    )

    # Caching Settings
    enable_caching: bool = Field(default=True, description="Enable resource caching")
    cache_max_age_days: int = Field(
        default=30, ge=1, description="Maximum age of cached resources in days"
    )

    # Parallel Processing
    max_parallel_tasks: int = Field(
        default=3, ge=1, description="Maximum number of parallel tasks"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string",
    )
    log_file: Optional[Path] = Field(
        default=None, description="Path to log file (None for console only)"
    )

    # Experiment Tracking
    enable_experiments: bool = Field(
        default=False, description="Enable experiment tracking"
    )

    # Comic Generation Settings
    comic_style: str = Field(
        default="anime", description="Comic style: anime, comic, webtoon, ink"
    )
    comic_panel_style: str = Field(
        default="manga", description="Panel layout style: manga, western, webtoon"
    )
    default_panel_count: int = Field(
        default=4, ge=1, le=6, description="Default number of panels per scene"
    )
    comic_image_resolution: str = Field(
        default="1024*1024",
        description="Comic panel image resolution as WIDTH*HEIGHT string",
    )

    # Project Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent,
        description="Project root directory",
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
