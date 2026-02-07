from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.inventory import InventoryBatch,Inventory,ItemCategory, ItemPerishableNonPerishable
from sqlalchemy.orm import Session
from datetime import datetime,date
import logging


logger = logging.getLogger(__name__)


def calculate_days_until_expiry(expiry_date: datetime) -> int:
    today = datetime.utcnow().date()
    expiry = expiry_date.date() if hasattr(expiry_date,"date") else expiry_date
    return (expiry - today).days

def find_lifecycle_stage(
    days_until_expiry: int,
    fresh_threshold: int,
) -> str:
    if days_until_expiry < 0:
        return "EXPIRED"
    elif days_until_expiry <= fresh_threshold:
        return "NEAR_EXPIRY"
    else:
        return "FRESH" 
    
def update_batch_lifecycle(batch:InventoryBatch, item:Inventory, db:Session):
    if not batch.expiry_date:
        return
    
    days_until_expiry = calculate_days_until_expiry(batch.expiry_date)
    old_stage = batch.lifecycle_stage

    batch.lifecycle_stage = find_lifecycle_stage(
        days_until_expiry,
        item.fresh_threshold_days or 3,
    )

    if old_stage != batch.lifecycle_stage:
        logger.info(
            f"Batch {batch.id} lifecycle updated: {old_stage} -> {batch.lifecycle_stage}"
            f"(expires in {days_until_expiry} days)"
        )
        db.commit()

def update_inventory_lifecycle(item: Inventory, db: Session):
    if not item.expiry_date:
        return
    
    days_until_expiry = calculate_days_until_expiry(item.expiry_date)
    old_stage = item.lifecycle_stage

    item.lifecycle_stage = find_lifecycle_stage(
        days_until_expiry,
        item.fresh_threshold_days or 3
    )

    if old_stage != item.lifecycle_stage:
        logger.info(
            f"Inventory {item.id} lifecycle updated:"
            f"{old_stage} -> {item.lifecycle_stage}"
            f"(expires in {days_until_expiry} days)"
        )

@celery_app.task(name="app.tasks.update_all_batch_lifecycles")
def update_batch_lifecycles_status():
    db = SessionLocal()

    try:
        batches = (
            db.query(InventoryBatch)
            .join(Inventory)
            .join(ItemCategory, Inventory.item_category_id == ItemCategory.id)
            .filter(
                InventoryBatch.expiry_date.isnot(None),
                ItemCategory.category_type == ItemPerishableNonPerishable.PERISHABLE
            )
            .all()
)


        updated_count = 0

        for batch in batches:
            previous_stage = batch.lifecycle_stage
            update_batch_lifecycle(batch, batch.item, db)

            if previous_stage != batch.lifecycle_stage:
                updated_count += 1

        db.commit()

        logger.info(
            f"Batch lifecycle update completed. "
            f"Updated {updated_count}/{len(batches)} batches."
        )

        return {
            "status": "success",
            "total_batches": len(batches),
            "updated_batches": updated_count
        }

    except Exception as e:
        db.rollback()
        logger.exception("Error updating batch lifecycles")
        raise
    finally:
        db.close()

@celery_app.task(name="app.tasks.update_all_inventory_lifecycles")
def update_inventory_lifecycle_status():
    db = SessionLocal()

    try:
        items = (
            db.query(Inventory)
            .join(ItemCategory)
            .filter(
                Inventory.expiry_date.isnot(None),
                Inventory.is_active == True,
                ItemCategory.category_type == ItemPerishableNonPerishable.PERISHABLE
            )
            .all()
        )

        updated_count = 0

        for item in items:
            previous_stage = item.lifecycle_stage
            update_inventory_lifecycle(item, db)

            if previous_stage != item.lifecycle_stage:
                updated_count += 1

        db.commit()

        logger.info(
            f"Inventory lifecycle update completed. "
            f"Updated {updated_count}/{len(items)} items."
        )

        return {
            "status": "success",
            "total_items": len(items),
            "updated_items": updated_count
        }

    except Exception:
        db.rollback()
        logger.exception("Error updating inventory lifecycles")
        raise
    finally:
        db.close()
