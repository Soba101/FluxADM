"""
Configuration management for FluxADM
Handles environment-specific settings and validation
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with validation"""
    
    # Application
    APP_NAME: str = "FluxADM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "sqlite:///./fluxadm.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    
    # AI Services
    LOCAL_LLM_ENDPOINT: str = "http://127.0.0.1:1234"
    LOCAL_LLM_MODEL: str = "mistralai/mistral-small-3.2"
    AI_MODEL_PRIMARY: str = "local"  # Use local LLM only
    AI_MODEL_FALLBACK: str = "local"  # No external fallback
    AI_MAX_TOKENS: int = 2000  # Reduced for faster responses
    AI_TEMPERATURE: float = 0.1
    AI_TIMEOUT: int = 180  # 3 minutes for local inference
    AI_MAX_RETRIES: int = 2  # Reduced retries since each takes long
    
    # File Upload
    UPLOAD_FOLDER: str = "data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "doc", "docx", "txt", "rtf"]
    
    # Redis & Background Jobs
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Security
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ACCESS_TOKEN_EXPIRES: int = 24  # hours
    PASSWORD_HASH_ROUNDS: int = 12
    
    # Logging & Monitoring
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    PROMETHEUS_METRICS_PORT: int = 9090
    
    # Email Configuration
    EMAIL_SMTP_HOST: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USER: Optional[str] = None
    EMAIL_SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@fluxadm.com"
    
    # Slack Integration
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # LDAP/Active Directory
    LDAP_HOST: Optional[str] = None
    LDAP_PORT: int = 389
    LDAP_BASE_DN: Optional[str] = None
    LDAP_BIND_USER: Optional[str] = None
    LDAP_BIND_PASSWORD: Optional[str] = None
    
    # ServiceNow Integration
    SERVICENOW_INSTANCE: Optional[str] = None
    SERVICENOW_USERNAME: Optional[str] = None
    SERVICENOW_PASSWORD: Optional[str] = None
    
    @validator('UPLOAD_FOLDER')
    def create_upload_folder(cls, v):
        """Ensure upload folder exists"""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    @validator('ALLOWED_EXTENSIONS')
    def validate_extensions(cls, v):
        """Ensure extensions are lowercase"""
        return [ext.lower() for ext in v]
    
    @validator('MAX_FILE_SIZE_MB')
    def validate_file_size(cls, v):
        """Ensure reasonable file size limit"""
        if v <= 0 or v > 100:
            raise ValueError("File size must be between 1 and 100 MB")
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def database_echo(self) -> bool:
        """Enable SQLAlchemy query logging in debug mode"""
        return self.DEBUG
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


class DatabaseConfig:
    """Database configuration helper"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
    
    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")
    
    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql")
    
    @property
    def connection_args(self) -> dict:
        """Database-specific connection arguments"""
        if self.is_sqlite:
            return {"check_same_thread": False}
        return {}


class AIConfig:
    """AI service configuration helper"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def has_local_llm(self) -> bool:
        return bool(self.settings.LOCAL_LLM_ENDPOINT)
    
    @property
    def has_ai_services(self) -> bool:
        return self.has_local_llm
    
    @property
    def primary_service(self) -> str:
        """Determine primary AI service"""
        return "local"


# Global settings instance
settings = Settings()
db_config = DatabaseConfig(settings.DATABASE_URL)
ai_config = AIConfig(settings)


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_db_config() -> DatabaseConfig:
    """Get database configuration"""
    return db_config


def get_ai_config() -> AIConfig:
    """Get AI configuration"""
    return ai_config