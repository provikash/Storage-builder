
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import os
import json
from bot.logging import LOGGER

logger = LOGGER(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    uri: str
    name: str = "filetolinksdb"
    connection_timeout: int = 10000
    max_pool_size: int = 100

@dataclass
class CloneConfig:
    """Clone-specific configuration"""
    max_clones_per_user: int = 5
    startup_timeout: int = 30
    health_check_interval: int = 60
    auto_restart: bool = True
    max_restart_attempts: int = 3

@dataclass
class SecurityConfig:
    """Security configuration"""
    token_encryption_key: Optional[str] = None
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 30
    allowed_file_types: list = field(default_factory=lambda: ['.jpg', '.png', '.pdf', '.mp4', '.zip'])

@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    log_level: str = "INFO"
    metrics_enabled: bool = True
    health_check_endpoint: bool = True
    performance_tracking: bool = True

@dataclass
class ApplicationSettings:
    """Main application settings"""
    debug: bool = False
    environment: str = "production"
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(""))
    clone: CloneConfig = field(default_factory=CloneConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def from_env(cls) -> 'ApplicationSettings':
        """Create settings from environment variables"""
        return cls(
            debug=os.getenv("DEBUG", "False").lower() == "true",
            environment=os.getenv("ENVIRONMENT", "production"),
            database=DatabaseConfig(
                uri=os.getenv("DATABASE_URI", ""),
                name=os.getenv("DATABASE_NAME", "filetolinksdb")
            ),
            clone=CloneConfig(
                max_clones_per_user=int(os.getenv("MAX_CLONES_PER_USER", "5")),
                startup_timeout=int(os.getenv("CLONE_STARTUP_TIMEOUT", "30")),
                health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
            ),
            security=SecurityConfig(
                token_encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY"),
                rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true",
                max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
            ),
            monitoring=MonitoringConfig(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                metrics_enabled=os.getenv("METRICS_ENABLED", "True").lower() == "true"
            )
        )
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ApplicationSettings':
        """Create settings from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logger.warning(f"Failed to load settings from file {file_path}: {e}")
            return cls.from_env()
    
    def save_to_file(self, file_path: str):
        """Save settings to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.__dict__, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save settings to file {file_path}: {e}")

# Global settings instance
settings = ApplicationSettings.from_env()
