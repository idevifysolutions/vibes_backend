from datetime import datetime, date
from app.models.inventory import Inventory, InventoryBatch, PerishableLifecycle
from sqlalchemy.orm import Session


def calculate_days_until_expiry(expiry_date: date) -> int:
    """Calculate days until expiry (negative if expired)"""
    today = date.today()
    delta = expiry_date - today
    return delta.days

def calculate_hours_until_expiry(expiry_date: date) -> int:
    """Calculate hours until expiry (negative if expired)"""
    today = datetime.now()
    expiry_datetime = datetime.combine(expiry_date, datetime.min.time())
    delta = expiry_datetime - today
    return int(delta.total_seconds() / 3600)

def determine_lifecycle_stage(
    days_until_expiry: int,
    fresh_threshold: int = 3,
    near_expiry_threshold: int = 1
) -> PerishableLifecycle:
    """
    Determine lifecycle stage based on days until expiry
    
    Fresh: More than fresh_threshold days
    Near Expiry: Between near_expiry_threshold and fresh_threshold days
    Expired: Past expiry date (negative days)
    """
    if days_until_expiry < 0:
        return PerishableLifecycle.EXPIRED
    elif days_until_expiry <= near_expiry_threshold:
        return PerishableLifecycle.NEAR_EXPIRY
    elif days_until_expiry <= fresh_threshold:
        return PerishableLifecycle.NEAR_EXPIRY
    else:
        return PerishableLifecycle.FRESH

def update_batch_lifecycle(batch: InventoryBatch, item: Inventory):
    """Update batch lifecycle stage based on current date"""
    if not batch.expiry_date:
        return
    
    days_until_expiry = calculate_days_until_expiry(batch.expiry_date)
    
    batch.lifecycle_stage = determine_lifecycle_stage(
        days_until_expiry,
        item.fresh_threshold_days or 3,
        item.near_expiry_threshold_days or 1
    )

def generate_batch_number_sequential(
    item_id: int,
    db: Session,
    prefix: str = "BATCH"   
) -> str:
    # Get highest batch number for this item
    last_batch = db.query(InventoryBatch.batch_number)\
        .filter(InventoryBatch.inventory_item_id == item_id)\
        .filter(InventoryBatch.batch_number.like(f"{prefix}-%"))\
        .order_by(InventoryBatch.batch_number.desc())\
        .first()
    
    if last_batch:
        try:
            # Extract number from "BATCH-000001"
            last_num = int(last_batch[0].split("-")[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    batch_number = f"{prefix}-{str(new_num).zfill(6)}"
    
    return batch_number    
