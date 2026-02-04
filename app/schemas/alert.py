# app/schemas/alert.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.inventory import AlertType, AlertStatus

class AlertBase(BaseModel):
    alert_type: AlertType
    priority: str
    message: str

class AlertResponse(AlertBase):
    id: UUID4
    inventory_item_id: int
    batch_id: Optional[int]
    status: AlertStatus
    current_quantity: Optional[Decimal]
    threshold_value: Optional[Decimal]
    suggested_action: Optional[str]
    affected_dishes: Optional[str]
    alert_date: datetime
    acknowledged_by_user_id: Optional[int]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    # Include inventory item details
    inventory_item_name: Optional[str]
    
    class Config:
        from_attributes = True

class AlertUpdate(BaseModel):
    status: Optional[AlertStatus]
    
class AlertFilter(BaseModel):
    status: Optional[AlertStatus]
    alert_type: Optional[AlertType]
    priority: Optional[str]
    from_date: Optional[datetime]
    to_date: Optional[datetime]