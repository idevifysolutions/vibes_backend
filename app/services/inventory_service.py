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
from uuid import UUID


class InventoryService:
    """Service class for inventory operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_items(self) -> List[Inventory]:
        """Get all inventory items"""
        return self.db.query(Inventory).all()
    
    def get_item_by_id(self, item_id: int) -> Optional[Inventory]:
        """Get inventory item by ID"""
        return self.db.query(Inventory).filter(Inventory.id == item_id, Inventory.tenant_id == tenant_id,
                Inventory.is_active == True,).first()
    
    def search_items(
        self,
        tenant_id: UUID,
        name: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Inventory]:
        """Search inventory with filters"""
        query = self.db.query(Inventory).filter(
            Inventory.tenant_id == tenant_id,
            Inventory.is_active == True,
        )
        
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
        
        return query.order_by(Inventory.date_added.desc()).all()
    
    def update_item(self, item_id: int, tenant_id:UUID, item_update: InventoryUpdate):
        """Update inventory item"""
        item = (self.db.query(Inventory).filter(
            Inventory.id == item_id,
            Inventory.tenant_id == tenant_id,
            Inventory.is_active == True,
        ).first()
        )
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
        
        logger.info( "Updated inventory item %s (tenant=%s)",
        item.id,
        tenant_id,)
        return item
    
    def delete_item(self, item_id: int, tenant_id: UUID) -> bool:
        """Delete inventory item"""
        item = (
            self.db.query(Inventory)
            .filter(
                Inventory.id == item_id,
                Inventory.tenant_id == tenant_id,
                Inventory.is_active == True,
        )
        .first()
        )
        if not item:
            return False
        
        self.db.delete(item)
        self.db.commit()
        
        logger.info( "Deleted inventory item %s (tenant=%s)",
        item.id,
        tenant_id,)
        return True
    
    def delete_all_items(self) -> int:
        """Delete all inventory items"""
        count = self.db.query(Inventory).delete()
        self.db.commit()
        
        logger.warning(f"Deleted all inventory items: {count} items")
        return count