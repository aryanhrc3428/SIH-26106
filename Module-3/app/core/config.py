from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    
    DNS_TIMEOUT_SECONDS: float = 2.0
    DNS_CUSTOM_NAMESERVERS: str = "1.1.1.1,8.8.8.8"
    
    EVIDENCE_STAGING_DIR: str = "/tmp/sih_evidence_staging"

settings = Settings()

