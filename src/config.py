"""Configuration centralisée pour l'application TW3"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class NewsAPIConfig:
    """Configuration pour NewsAPI"""
    api_key: str
    base_url: str = "https://newsapi.org/v2"
    timeout: int = 10
    max_results: int = 5
    default_language: str = "fr"
    
    @classmethod
    def from_env(cls) -> 'NewsAPIConfig':
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            raise ValueError("NEWSAPI_KEY environment variable is required")
        return cls(api_key=api_key)


@dataclass  
class ModelConfig:
    """Configuration pour le modèle Qwen"""
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    max_new_tokens: int = 4096
    temperature: float = 0.7
    device_map: str = "auto"
    trust_remote_code: bool = True


@dataclass
class LoggingConfig:
    """Configuration pour les logs"""
    log_dir: str = "/app/volume/conversations"
    log_level: str = "INFO"
    structured_logs: bool = True
    retention_days: int = 90


@dataclass
class ResilienceConfig:
    """Configuration pour la resilience"""
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    rate_limit_calls_per_hour: int = 100


@dataclass
class SecurityConfig:
    """Configuration pour la sécurité"""
    cors_origins: list = None
    api_key_header: str = "X-API-Key"
    max_request_size: int = 1024 * 1024  # 1MB
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]  # À restreindre en production


@dataclass
class AppConfig:
    """Configuration principale de l'application"""
    news_api: NewsAPIConfig
    model: ModelConfig
    logging: LoggingConfig
    resilience: ResilienceConfig
    security: SecurityConfig
    
    # Métadonnées de l'application
    app_name: str = "TW3 Chat Backend"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Charge la configuration depuis les variables d'environnement"""
        return cls(
            news_api=NewsAPIConfig.from_env(),
            model=ModelConfig(),
            logging=LoggingConfig(),
            resilience=ResilienceConfig(),
            security=SecurityConfig(),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )


# Instance globale de configuration
config = AppConfig.load()
