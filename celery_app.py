# backend/celery_app.py
from celery import Celery
from config import config

celery_app = Celery(
    "sms_system",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=["routes.sms"],  # ensure tasks defined in routes.sms are discovered
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_pool='solo',
    
)


    
