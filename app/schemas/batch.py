from decimal import Decimal
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

class UnitType(str, Enum):
    kg = "kg"
    gm = "gm"
    mg = "mg"
    liter = "liter"
    ml = "ml"
class BatchCreate(BaseModel):
    expiry_date: date | None = None
    batch_number: Optional[str] = None

    quantity_received: Decimal

    packets: int | None = None
    pieces: int | None = None
    total_pieces: int | None = None

    price_per_packet: float | None = None
    price_per_piece: float | None = None
    unit_cost: Decimal | None = None
    unit: UnitType
    
    # batch_number: str
    # quantity_received: float
    # packets: int | None = None
    # pieces: int | None = None
    # total_pieces: int | None = None
    # expiry_date: date
    # manufacture_date: Optional[date] = None
    # unit_cost: float
    # supplier_info: Optional[str] = None
    # quality_notes: Optional[str] = None

class BatchResponse(BaseModel):
    id: int
    inventory_item_id :int
    user_id: int
    batch_number: str
    quantity_received: float
    quantity_remaining: float
    expiry_date: date
    manufacture_date: Optional[date]
    days_until_expiry: int
    hours_until_expiry: int
    lifecycle_stage: str
    is_expired: bool
    unit_cost: float
    
    class Config:
        from_attributes = True    

class PerishableItemResponse(BaseModel):
    id: int
    name: str
    sku: str
    current_quantity: float
    total_batches: int
    expiring_soon_count: int
    expired_count: int
    oldest_expiry_date: Optional[date]
    batches: List[BatchResponse]        