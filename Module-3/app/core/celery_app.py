from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "module3_forensics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker"]
)

celery_app.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
