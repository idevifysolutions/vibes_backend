"""
app/api/v1/endpoints/inventory.py
Inventory management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db
# from app.schemas.inventory import (
#     InventoryCreate, InventoryOut, InventoryUpdate, InventorySearch
# )
from app.models.expense import Expense
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryOut,InventoryUpdate,InventoryItemCreate
from app.services.inventory_service import InventoryService

router = APIRouter()



@router.post("/add_item")
def add_item(
    item: InventoryItemCreate,
    db: Session = Depends(get_db)
):

    if item.price_per_unit is not None:
        total_cost = item.quantity * item.price_per_unit
        price_per_unit = item.price_per_unit
    elif total_cost is not None:
        total_cost = item.total_cost
        price_per_unit = 0.0
        
    else:
        raise HTTPException(status_code=400, detail="Either price_per_unit or total_cost must be provided")


    inventory_item = Inventory(
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        price_per_unit=price_per_unit if price_per_unit is not None else 0.0,
        total_cost=total_cost,
        type=item.type if type is not None else "",
        date_added=item.date_added or datetime.utcnow()
    )

    db.add(inventory_item)
    db.add(Expense(item_name=item.name, quantity=item.quantity, total_cost=total_cost, date=item.date_added or datetime.utcnow()))
    db.commit()
    db.refresh(inventory_item)

    inventory = db.query(Inventory).all()
    return {"message": "Item added successfully!", "inventory": inventory}

@router.get("/", response_model=List[InventoryOut])
def get_all_inventory(db: Session = Depends(get_db)):
    """Get all inventory items"""
    service = InventoryService(db)
    return service.get_all_items()


@router.get("/search", response_model=List[InventoryOut])
def search_inventory(
    name: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search inventory with filters"""
    service = InventoryService(db)
    return service.search_items(
        name=name,
        type=type,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/{item_id}", response_model=InventoryOut)
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    print("RRRRRRRRRRRR")
    """Get single inventory item by ID"""
    service = InventoryService(db)
    item = service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=InventoryOut)
def update_inventory_item(
    item_id: int,
    item_update: InventoryUpdate,
    db: Session = Depends(get_db)
):
    """Update inventory item"""
    service = InventoryService(db)
    updated_item = service.update_item(item_id, item_update)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item


@router.delete("/{item_id}")
def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    """Delete inventory item"""
    service = InventoryService(db)
    success = service.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


@router.delete("/")
def delete_all_inventory(
    confirm: bool = Query(False, description="Confirm deletion"),
    db: Session = Depends(get_db)
):
    """Delete all inventory items (use with caution)"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm deletion by setting confirm=true"
        )
    
    service = InventoryService(db)
    deleted_count = service.delete_all_items()
    return {
        "message": f"Deleted {deleted_count} item(s) from inventory"
    }