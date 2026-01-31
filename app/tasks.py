from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.inventory import InventoryBatch,Inventory,ItemCategory
from sqlalchemy.orm import Session
from datetime import datetime,date
import logging


logger = logging.getLogger(__name__)


def calculate_days_until_expiry(expiry_date: datetime) -> int:
    return (expiry_date - datetime.now().date()).days


def find_lifecycle_stage(
    days_until_expiry: int,
    fresh_threshold: int,
    near_expiry_threshold: int    
) -> str:
    if days_until_expiry < 0:
        return "expired"
    elif days_until_expiry <= near_expiry_threshold:
        return "near_expiry"
    elif days_until_expiry <= fresh_threshold:
        return "aging"
    else:
        return "fresh" 
    
def update_batch_lifecycle(batch, item, db):
    if not batch.expiry_date:
        return
    
    days_until_expiry = calculate_days_until_expiry(batch.expiry_date)
    old_stage = batch.lifecycle_stage

    batch.lifecycle_stage = find_lifecycle_stage(
        days_until_expiry,
        item.fresh_threshold_days or 3,
        item.near_expiry_threshold_days or 1
    )

    if old_stage != batch.lifecycle_stage:
        logger.info(
            f"Batch {batch.id} lifecycle updated: {old_stage} -> {batch.lifecycle_stage}"
            f"(expires in {days_until_expiry} days)"
        )
        db.commit()

@celery_app.task(name="app.tasks.update_all_batch_lifecycles")
def update_batch_lifecycles_status():
    db = SessionLocal()

    try: 
        batches = db.query(InventoryBatch).join(Inventory).filter(
            InventoryBatch.expiry_date.isnot(None),
            ItemCategory.category_type == "PERISHABLE"
        ).all()

        updated_count = 0
        for batch in batches:
            previous_batch = batch.lifecycle_stage
            update_batch_lifecycle(batch, batch.item, db)

            if previous_batch != batch.lifecycle_stage:
                updated_count += 1

        logger.info(f"Batch lifecycle update completed. Updated {updated_count} batches.") 
        return {
            "status" : "success",
            "total_batches": len(batches),
            "updated_batches": updated_count
        }              
    
    except Exception as e:
        logger.error(f"Error updating batch lifecycles: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()