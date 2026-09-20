from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    """Application settings."""

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BIS Compass"

    # NVIDIA API settings
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_CHAT_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    NVIDIA_EMBED_MODEL: str = "nvidia/nemotron-3-embed-1b"
    NVIDIA_FALLBACK_CHAT_MODEL: str = "mistralai/mistral-nemotron"

    # Groq API settings
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_CHAT_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_CHAT_MODEL: str = "mixtral-8x7b-32768"

    # Security settings
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    BACKEND_CORS_ORIGINS: List[Union[str, str]] = ["http://localhost:3000"]

    # Application settings
    USER_AGENT: str = "BIS-Compass/1.0 (+https://github.com/your-org/bis-compass)"
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3

    # Cache settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour

    # Upload settings
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "/app/uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment

def get_settings() -> Settings:
    """Get application settings."""
    return Settings()