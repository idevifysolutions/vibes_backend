"""
app/services/inventory_service.py
Business logic for inventory management
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.inventory import Inventory
from app.models.expense import Expense
from app.schemas.inventory import  InventoryUpdate
from app.utils.date_helpers import parse_date
from app.core.logging import logger


class InventoryService:
    """Service class for inventory operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # def add_item(self, item_data: InventoryCreate) -> Inventory:
    #     """Add a new inventory item"""
    #     # Calculate total_cost if not provided
    #     if item_data.price_per_unit is not None:
    #         total_cost = item_data.quantity * item_data.price_per_unit
    #     elif item_data.total_cost is not None:
    #         total_cost = item_data.total_cost
    #     else:
    #         raise ValueError("Either price_per_unit or total_cost must be provided")
        
    #     # Calculate price_per_unit if not provided
    #     price_per_unit = item_data.price_per_unit
    #     if price_per_unit is None:
    #         price_per_unit = total_cost / item_data.quantity if item_data.quantity > 0 else 0
        
    #     # Create inventory item
    #     item = Inventory(
    #         name=item_data.name,
    #         quantity=item_data.quantity,
    #         unit=item_data.unit,
    #         price_per_unit=price_per_unit,
    #         total_cost=total_cost,
    #         type=item_data.type or "",
    #         date_added=item_data.date_added or datetime.utcnow()
    #     )
        
    #     self.db.add(item)
        
    #     # Create expense record
    #     expense = Expense(
    #         item_name=item_data.name,
    #         quantity=item_data.quantity,
    #         total_cost=total_cost,
    #         date=item.date_added
    #     )
    #     self.db.add(expense)
        
    #     self.db.commit()
    #     self.db.refresh(item)
        
    #     logger.info(f"Added inventory item: {item.name} ({item.quantity} {item.unit})")
    #     return item
    
    def get_all_items(self) -> List[Inventory]:
        """Get all inventory items"""
        return self.db.query(Inventory).all()
    
    def get_item_by_id(self, item_id: int) -> Optional[Inventory]:
        """Get inventory item by ID"""
        return self.db.query(Inventory).filter(Inventory.id == item_id).first()
    
    def search_items(
        self,
        name: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Inventory]:
        """Search inventory with filters"""
        query = self.db.query(Inventory)
        
        if name:
            query = query.filter(Inventory.name.ilike(f"%{name}%"))
        elif type:  # Only apply type filter if name is not provided
            query = query.filter(Inventory.type.ilike(f"%{type}%"))
        
        if start_date:
            start = parse_date(start_date)
            query = query.filter(Inventory.date_added >= start)
        
        if end_date:
            end = parse_date(end_date)
            query = query.filter(Inventory.date_added <= end)
        
        return query.all()
    
    def update_item(self, item_id: int, item_update: InventoryUpdate) -> Optional[Inventory]:
        """Update inventory item"""
        item = self.get_item_by_id(item_id)
        if not item:
            return None
        
        # Update fields if provided
        update_data = item_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(item, field, value)
        
        # Recalculate total_cost if quantity or price changed
        if 'quantity' in update_data or 'price_per_unit' in update_data:
            item.total_cost = item.quantity * item.price_per_unit
        
        self.db.commit()
        self.db.refresh(item)
        
        logger.info(f"Updated inventory item: {item.name}")
        return item
    
    def delete_item(self, item_id: int) -> bool:
        """Delete inventory item"""
        item = self.get_item_by_id(item_id)
        if not item:
            return False
        
        self.db.delete(item)
        self.db.commit()
        
        logger.info(f"Deleted inventory item: {item.name}")
        return True
    
    def delete_all_items(self) -> int:
        """Delete all inventory items"""
        count = self.db.query(Inventory).delete()
        self.db.commit()
        
        logger.warning(f"Deleted all inventory items: {count} items")
        return count