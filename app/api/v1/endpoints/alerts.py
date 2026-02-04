# app/api/v1/endpoints/alerts.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.api import deps
from app.models.users import User
from app.schemas.alert import AlertResponse, AlertUpdate, AlertFilter
from app.services.alert_service import AlertService
from app.models.inventory import InventoryAlert, AlertStatus, AlertType
from app.utils.auth_helper import get_current_user

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
def get_alerts(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[AlertStatus] = None,
    alert_type: Optional[AlertType] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all alerts with optional filtering"""
    query = db.query(InventoryAlert).filter(
        InventoryAlert.tenant_id == current_user.tenant_id
    )
    
    if status:
        query = query.filter(InventoryAlert.status == status)
    if alert_type:
        query = query.filter(InventoryAlert.alert_type == alert_type)
    if priority:
        query = query.filter(InventoryAlert.priority == priority)
    
    alerts = query.order_by(
        InventoryAlert.priority.desc(),
        InventoryAlert.alert_date.desc()
    ).offset(skip).limit(limit).all()
    
    return alerts

@router.get("/active", response_model=List[AlertResponse])
def get_active_alerts(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active alerts"""
    alerts = db.query(InventoryAlert).filter(
        InventoryAlert.tenant_id == current_user.tenant_id,
        InventoryAlert.status == AlertStatus.ACTIVE
    ).order_by(
        InventoryAlert.priority.desc(),
        InventoryAlert.alert_date.desc()
    ).all()
    
    return alerts

@router.get("/stats")
def get_alert_statistics(
    db: Session = Depends(deps.get_db),
    current_user :User = Depends(get_current_user)
):
    """Get alert statistics"""
    from sqlalchemy import func
    
    stats = db.query(
        InventoryAlert.alert_type,
        InventoryAlert.status,
        func.count(InventoryAlert.id).label('count')
    ).filter(
        InventoryAlert.tenant_id == current_user.tenant_id
    ).group_by(
        InventoryAlert.alert_type,
        InventoryAlert.status
    ).all()
    
    return {
        "statistics": [
            {
                "alert_type": stat.alert_type.value,
                "status": stat.status.value,
                "count": stat.count
            }
            for stat in stats
        ]
    }

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an alert"""
    alert_service = AlertService(db, current_user.tenant_id)
    alert = alert_service.acknowledge_alert(alert_id, current_user.id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert acknowledged successfully", "alert": alert}

@router.post("/{alert_id}/snooze")
def snooze_alert(
    alert_id: str,
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(get_current_user)
):
    """Snooze an alert for specified hours"""
    from datetime import timedelta
    
    snooze_until = datetime.now() + timedelta(hours=hours)
    alert_service = AlertService(db, current_user.tenant_id)
    alert = alert_service.snooze_alert(alert_id, snooze_until)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "message": f"Alert snoozed for {hours} hours",
        "alert": alert,
        "snooze_until": snooze_until
    }

@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    db: Session = Depends(deps.get_db),
    current_user:User = Depends(get_current_user)
):
    """Manually resolve an alert"""
    alert = db.query(InventoryAlert).filter(
        InventoryAlert.id == alert_id,
        InventoryAlert.tenant_id == current_user.tenant_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now()
    db.commit()
    
    return {"message": "Alert resolved successfully", "alert": alert}

@router.post("/trigger-check")
def trigger_alert_check(
    db: Session = Depends(deps.get_db),
    current_user:User = Depends(get_current_user)
):
    """Manually trigger alert check (useful for testing)"""
    alert_service = AlertService(db, current_user.tenant_id)
    alert_service.check_and_create_alerts()
    
    return {"message": "Alert check completed"}