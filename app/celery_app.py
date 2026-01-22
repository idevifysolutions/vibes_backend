from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "vibes_backend",
    broker=os.getenv("CELERY_BROKER_URL","redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND","redis://localhost:6379/0"),
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True
)

celery_app.conf.beat_schedule  = {
    "update-batch-lifecycles":{
        "task": "app.tasks.update_all_batch_lifecycles",
        # "schedule":crontab(hour=0,minute=0),
        "schedule":60.0
    }
}