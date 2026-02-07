from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "vibes_backend",
    broker=os.getenv("CELERY_BROKER_URL","redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND","redis://localhost:6379/0"),
    include=["app.tasks","app.alert_tasks",]
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
    },
       # NEW: Check inventory alerts every hour
    "check-inventory-alerts-hourly": {
        "task": "app.alert_tasks.check_inventory_alerts",
        # "schedule": 3600.0,  # Every hour (3600 seconds)
         "schedule":60.0
    },
    
    # NEW: Daily expiry digest at 8 AM
    "daily-expiry-digest": {
        "task": "app.alert_tasks.send_daily_expiry_digest",
        # "schedule": crontab(hour=8, minute=0),  # Daily at 8:00 AM UTC
         "schedule":60.0
    },
    "update-inventory-lifecycle-daily":{
        "task":"app.tasks.update_all_inventory_lifecycles",
        # "schedule": crontab(hour=1, minute=5),
         "schedule":60.0
    },
    # # NEW: Cleanup resolved alerts daily at midnight
    # "cleanup-resolved-alerts": {
    #     "task": "app.alert_tasks.cleanup_old_resolved_alerts",
    #     # "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    #      "schedule":60.0
    # },
    
    # # NEW: Send critical expiry alerts twice daily (morning and evening)
    # "critical-expiry-reminder": {
    #     "task": "app.alert_tasks.send_critical_expiry_reminders",
    #     # "schedule": crontab(hour="8,18", minute=0),  # 8 AM and 6 PM UTC
    #      "schedule":60.0
    # },
}