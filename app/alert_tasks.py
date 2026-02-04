# app/tasks/alert_tasks.py
from app.celery_app import Celery
from app.db.session import SessionLocal
from app.services.alert_service import AlertService
from app.models.tenants import Tenant

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def check_inventory_alerts():
    """Scheduled task to check for alerts"""
    db = SessionLocal()
    try:
        # Get all tenants
        from app.models import Tenant
        tenants = db.query(Tenant).all()
        
        for tenant in tenants:
            alert_service = AlertService(db, tenant.tenant_id)
            alert_service.check_and_create_alerts()
    finally:
        db.close()

@celery_app.task
def send_daily_expiry_digest():
    """Send daily summary of expiring items"""
    db = SessionLocal()
    try:
      
        
        tenants = db.query(Tenant).all()
        
        for tenant in tenants:
            alert_service = AlertService(db, tenant.tenant_id)
            # Implement daily digest logic
    finally:
        db.close()

# # Schedule configuration
# celery_app.conf.beat_schedule = {
#     'check-alerts-every-hour': {
#         'task': 'app.tasks.alert_tasks.check_inventory_alerts',
#         'schedule': 3600.0,  # Every hour
#     },
#     'daily-expiry-digest': {
#         'task': 'app.tasks.alert_tasks.send_daily_expiry_digest',
#         'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
#     },
# }