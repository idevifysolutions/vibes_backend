# app/services/alert_service.py
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.inventory import (
    Inventory, InventoryBatch, InventoryAlert, AlertType, 
    AlertStatus, ItemCategory
)
from app.services.notification_service import NotificationService

class AlertService:
    def __init__(self, db: Session, tenant_id: UUID, branch_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id
        # self.branch_id = branch_id
        
    
    def check_and_create_alerts(self):
        """Main method to check all alert conditions"""
        self.check_low_stock_alerts()
        self.check_out_of_stock_alerts()
        self.check_expiry_alerts()
        self.cleanup_resolved_alerts()
        self.check_batch_empty_alerts() 

    def check_batch_empty_alerts(self):
        """Check for batches that are completely depleted"""
    
    # Get all active batches with no remaining quantity
        empty_batches = self.db.query(InventoryBatch).join(Inventory).filter(
            InventoryBatch.tenant_id == self.tenant_id,
            InventoryBatch.is_active == True,
            InventoryBatch.quantity_remaining <= 0
        ).all()
        
        for batch in empty_batches:
            # Check if alert already exists
            existing_alert = self.db.query(InventoryAlert).filter(
                InventoryAlert.batch_id == batch.id,
                InventoryAlert.alert_type == AlertType.BATCH_EMPTY,
                InventoryAlert.status == AlertStatus.ACTIVE
            ).first()
            
            if not existing_alert:
                self._create_alert(
                    inventory_item=batch.item,
                    batch_id=batch.id,
                    alert_type=AlertType.BATCH_EMPTY,
                    message=f"Batch {batch.batch_number} of {batch.item.name} is depleted",
                    current_quantity=Decimal(0),
                    threshold_value=batch.quantity_received,
                    suggested_action=f"Mark batch as inactive or reorder",
                    priority="medium"
                )    
        

    def check_low_stock_alerts(self):
        """Check for items below reorder point"""
        query = self.db.query(Inventory).filter(
            Inventory.tenant_id == self.tenant_id,
            Inventory.is_active == True,
            Inventory.current_quantity < Inventory.reorder_point,
            Inventory.current_quantity > 0  # Not out of stock
        )
        
        # if self.branch_id:
        #     query = query.filter(Inventory.branch_id == self.branch_id)
        
        low_stock_items = query.all()
        
        for item in low_stock_items:
            # Check if alert already exists and is active
            existing_alert = self.db.query(InventoryAlert).filter(
                InventoryAlert.inventory_item_id == item.id,
                InventoryAlert.alert_type == AlertType.LOW_STOCK,
                InventoryAlert.status == AlertStatus.ACTIVE
            ).first()
            
            if not existing_alert:
                self._create_alert(
                    inventory_item=item,
                    alert_type=AlertType.LOW_STOCK,
                    message=f"Low stock alert: {item.name} is at {item.current_quantity} {item.unit}",
                    current_quantity=item.current_quantity,
                    threshold_value=item.reorder_point,
                    suggested_action=f"Consider ordering {item.reorder_quantity} {item.unit}",
                    priority="medium"
                )
    
    def check_out_of_stock_alerts(self):
        """Check for items that are completely out of stock"""
        query = self.db.query(Inventory).filter(
            Inventory.tenant_id == self.tenant_id,
            Inventory.is_active == True,
            Inventory.current_quantity <= 0
        )
        
        # if self.branch_id:
        #     query = query.filter(Inventory.branch_id == self.branch_id)
        
        out_of_stock_items = query.all()
        
        for item in out_of_stock_items:
            existing_alert = self.db.query(InventoryAlert).filter(
                InventoryAlert.inventory_item_id == item.id,
                InventoryAlert.alert_type == AlertType.OUT_OF_STOCK,
                InventoryAlert.status == AlertStatus.ACTIVE
            ).first()
            
            if not existing_alert:
                # Find affected dishes
                affected_dishes = self._get_affected_dishes(item.id)
                
                self._create_alert(
                    inventory_item=item,
                    alert_type=AlertType.OUT_OF_STOCK,
                    message=f"CRITICAL: {item.name} is out of stock",
                    current_quantity=Decimal(0),
                    threshold_value=item.reorder_point,
                    suggested_action=f"Immediate reorder required: {item.reorder_quantity} {item.unit}",
                    affected_dishes=affected_dishes,
                    priority="critical"
                )
    
    def check_expiry_alerts(self):
        """Check for batches approaching expiry"""
        # Get all active batches with expiry dates
        batches = self.db.query(InventoryBatch).join(Inventory).filter(
            InventoryBatch.tenant_id == self.tenant_id,
            InventoryBatch.is_active == True,
            InventoryBatch.quantity_remaining > 0,
            InventoryBatch.expiry_date.isnot(None)
        ).all()
        
        today = datetime.now().date()
        
        for batch in batches:
            days_to_expiry = (batch.expiry_date - today).days
            
            # Get threshold from item or use default
            threshold = batch.item.expiry_alert_threshold_days or 3
            
            if days_to_expiry <= threshold and days_to_expiry >= 0:
                # Check if alert already exists for this batch
                existing_alert = self.db.query(InventoryAlert).filter(
                    InventoryAlert.batch_id == batch.id,
                    InventoryAlert.alert_type == AlertType.EXPIRY_WARNING,
                    InventoryAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.SNOOZED])
                ).first()
                
                if not existing_alert:
                    # Get dishes that can use this ingredient
                    suggested_dishes = self._get_suggested_dishes_for_expiring_item(
                        batch.inventory_item_id
                    )
                    
                    priority = "critical" if days_to_expiry <= 1 else "high"
                    
                    self._create_alert(
                        inventory_item=batch.item,
                        batch_id=batch.id,
                        alert_type=AlertType.EXPIRY_WARNING,
                        message=f"{batch.item.name} (Batch: {batch.batch_number}) expires in {days_to_expiry} days",
                        current_quantity=batch.quantity_remaining,
                        threshold_value=Decimal(threshold),
                        suggested_action=f"Use in: {suggested_dishes}" if suggested_dishes else "Mark as waste if cannot use",
                        priority=priority
                    )
            
            # Handle already expired items
            elif days_to_expiry < 0:
                existing_alert = self.db.query(InventoryAlert).filter(
                    InventoryAlert.batch_id == batch.id,
                    InventoryAlert.alert_type == AlertType.EXPIRY_WARNING,
                    InventoryAlert.status == AlertStatus.ACTIVE
                ).first()
                
                if existing_alert:
                    # Update message to indicate expired
                    existing_alert.message = f"EXPIRED: {batch.item.name} (Batch: {batch.batch_number}) expired {abs(days_to_expiry)} days ago"
                    existing_alert.priority = "critical"
                    existing_alert.suggested_action = "Mark as waste immediately"
    
    def _create_alert(
        self,
        inventory_item: Inventory,
        alert_type: AlertType,
        message: str,
        current_quantity: Decimal,
        threshold_value: Decimal,
        suggested_action: str,
        batch_id: Optional[int] = None,
        affected_dishes: Optional[str] = None,
        priority: str = "medium"
    ):
        """Create a new alert"""
        alert = InventoryAlert(
            tenant_id=self.tenant_id,
            # branch_id=self.branch_id,
            inventory_item_id=inventory_item.id,
            batch_id=batch_id,
            alert_type=alert_type,
            status=AlertStatus.ACTIVE,
            priority=priority,
            message=message,
            current_quantity=current_quantity,
            threshold_value=threshold_value,
            suggested_action=suggested_action,
            affected_dishes=affected_dishes,
            alert_date=datetime.now()
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Trigger notification delivery
        self._send_notifications(alert)
        
        return alert
    
    def _get_affected_dishes(self, inventory_item_id: int) -> Optional[str]:
        """Get list of dishes that cannot be prepared due to missing ingredient"""
        # This assumes you have a Dish and DishIngredient model
        # Adjust based on your actual schema
        try:
            from app.models import Dish, DishIngredient
            
            dishes = self.db.query(Dish).join(DishIngredient).filter(
                DishIngredient.inventory_item_id == inventory_item_id,
                Dish.is_active == True
            ).all()
            
            if dishes:
                return ", ".join([dish.name for dish in dishes])
        except:
            pass
        
        return None
    
    def _get_suggested_dishes_for_expiring_item(self, inventory_item_id: int) -> Optional[str]:
        """Get dishes that can use the expiring ingredient"""
        try:
            from app.models import Dish, DishIngredient
            
            dishes = self.db.query(Dish).join(DishIngredient).filter(
                DishIngredient.inventory_item_id == inventory_item_id,
                Dish.is_active == True
            ).limit(5).all()
            
            if dishes:
                return ", ".join([dish.name for dish in dishes[:3]])
        except:
            pass
        
        return None
    
    def _send_notifications(self, alert: InventoryAlert):
        """Queue notifications for delivery"""
        # This will be implemented in the notification service
        #         
        notification_service = NotificationService(self.db)
        notification_service.send_alert_notifications(alert)
    
    def cleanup_resolved_alerts(self):
        now = datetime.utcnow()

        # --- LOW STOCK → RESOLVED ---
        low_stock_subq = (
            self.db.query(InventoryAlert.id)
            .join(Inventory)
            .filter(
                InventoryAlert.tenant_id == self.tenant_id,
                InventoryAlert.alert_type == AlertType.LOW_STOCK,
                InventoryAlert.status == AlertStatus.ACTIVE,
                Inventory.current_quantity >= Inventory.reorder_point,
            )
            .subquery()
        )

        self.db.query(InventoryAlert).filter(
            InventoryAlert.id.in_(select(low_stock_subq.c.id))
        ).update(
            {
                InventoryAlert.status: AlertStatus.RESOLVED,
                InventoryAlert.resolved_at: now,
            },
            synchronize_session=False,
        )

        # --- OUT OF STOCK → RESOLVED ---
        out_of_stock_subq = (
            self.db.query(InventoryAlert.id)
            .join(Inventory)
            .filter(
                InventoryAlert.tenant_id == self.tenant_id,
                InventoryAlert.alert_type == AlertType.OUT_OF_STOCK,
                InventoryAlert.status == AlertStatus.ACTIVE,
                Inventory.current_quantity > 0,
            )
            .subquery()
        )

        self.db.query(InventoryAlert).filter(
            InventoryAlert.id.in_(select(out_of_stock_subq.c.id))
        ).update(
            {
                InventoryAlert.status: AlertStatus.RESOLVED,
                InventoryAlert.resolved_at: now,
            },
            synchronize_session=False,
        )

        self.db.commit()
    def acknowledge_alert(self, alert_id: str, user_id: int) -> InventoryAlert:
        """Mark alert as acknowledged"""
        alert = self.db.query(InventoryAlert).filter(
            InventoryAlert.id == alert_id,
            InventoryAlert.tenant_id == self.tenant_id
        ).first()
        
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by_user_id = user_id
            alert.acknowledged_at = datetime.now()
            self.db.commit()
            self.db.refresh(alert)
        
        return alert
    
    def snooze_alert(self, alert_id: str, snooze_until: datetime) -> InventoryAlert:
        """Snooze alert until specified time"""
        alert = self.db.query(InventoryAlert).filter(
            InventoryAlert.id == alert_id,
            InventoryAlert.tenant_id == self.tenant_id
        ).first()
        
        if alert:
            alert.status = AlertStatus.SNOOZED
            # You may want to add a snooze_until field to the model
            self.db.commit()
            self.db.refresh(alert)
        
        return alert