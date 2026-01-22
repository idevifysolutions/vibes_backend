from sqlalchemy import  Column, Integer, String, DateTime, Boolean, Numeric,ForeignKey, Text, Date, CheckConstraint, Index, Enum,Float
from datetime import datetime
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.base import Base
from sqlalchemy.orm import relationship
from app.db.mixins import TenantMixin
from sqlalchemy.dialects.postgresql import UUID
import uuid

class PerishableLifecycle(PyEnum):
    FRESH = "fresh"
    NEAR_EXPIRY = "near_expiry"
    EXPIRED = "expired"

class ItemPerishableNonPerishable(str,PyEnum):
    PERISHABLE="perishable"
    NON_PERISHABLE="non_perishable"   

class TransactionType(PyEnum):
    PURCHASE = "purchase"
    PREPARATION = "preparation"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    WASTAGE = "wastage"

class AlertType(PyEnum):
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRY_WARNING = "expiry_warning"
    # HIGH_WASTAGE = "high_wastage" 

class AlertStatus(PyEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"       

class Inventory(TenantMixin,Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.id"),nullable=False)
    item_category_id = Column(Integer,ForeignKey("item_categories.id"),nullable=False)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    name = Column(String, index=True, nullable=False)
    sku = Column(String(100), unique=True ,nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    type = Column(String, default="")
    expiry_date = Column(Date)
    purchase_unit = Column(String, nullable=False)
    purchase_unit_size = Column(Integer, nullable=False)
    shelf_life_in_days = Column(Integer)
    reorder_point = Column(Numeric(12, 3))
    reorder_quantity = Column(Numeric(12, 3))
    unit_cost = Column(Numeric(10, 2))
    expiry_alert_threshold_days = Column(Integer, default=3)
    fresh_threshold_days = Column(Integer, default=3)
    near_expiry_threshold_days = Column(Integer, default=1)
    current_quantity = Column(Numeric(12, 3), default=0)

    is_active = Column(Boolean,default=True)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(),onupdate=func.now(),default=datetime.utcnow)


    storage_location = relationship("StorageLocation")
    batches = relationship("InventoryBatch" , back_populates="item", cascade="all,delete-orphan")
    item_category = relationship("ItemCategory", back_populates="inventory_items")
    transactions = relationship("InventoryTransaction", back_populates="inventory")
    alerts = relationship("InventoryAlert", back_populates="inventory")
    user = relationship("User")

    # __table_args__ = (
    #     Index("idx_inventory_tenant_branch_sku", "tenant_id", "branch_id", "sku", unique=True),
    #     Index("idx_inventory_tenant", "tenant_id"),
    #     CheckConstraint("current_quantity >= 0", name="check_positive_quantity"),
    # )


    def __repr__(self):
        return f"<Inventory(name={self.name}, quantity={self.quantity} {self.unit})>"
    

class InventoryBatch(TenantMixin,Base):
    __tablename__ = "inventory_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    batch_number = Column(String(100), nullable=False)
    expiry_date = Column(Date)
    quantity_received = Column(Numeric(12, 3), nullable=True)
    quantity_remaining = Column(Numeric(12, 3), nullable=True)
    packets = Column(Integer, nullable=True)
    pieces = Column(Integer, nullable=True)
    total_pieces = Column(Integer, nullable=True)
    price_per_packet = Column(Float)
    price_per_piece = Column(Float)
    unit_cost = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    lifecycle_stage = Column(Enum(PerishableLifecycle))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    item = relationship("Inventory", back_populates="batches")
    transaction = relationship("InventoryTransaction", back_populates="batch")
    user = relationship("User")
    # __table_args__ = (
    #     Index("idx_batch_tenant", "tenant_id"),
    #     Index("idx_batch_tenant_expiry", "tenant_id", "expiry_date"),
    #     Index("idx_batch_tenant_item", "tenant_id", "inventory_item_id"),
    #     CheckConstraint("quantity_remaining >= 0", name="check_batch_positive_qty"),
    #     CheckConstraint("quantity_remaining <= quantity_received", name="check_batch_qty_logic"),
    # )
    
class PreparedMaterial(TenantMixin,Base):
    __tablename__ = "pre_preparedmaterial"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    storage_location_id = Column(Integer,ForeignKey("storage_locations.id", ondelete="CASCADE"),nullable=True)
    name = Column(String,index=True,nullable=False)

    inventory_item = relationship("Inventory")
    user = relationship("User")

class StorageLocation(TenantMixin,Base):
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    name = Column(String(100), nullable=False)
    storage_temp_min = Column(Numeric(5, 2))
    storage_temp_max = Column(Numeric(5, 2))
    special_handling_instructions = Column(Text)
    is_active = Column(Boolean, default=True)

    user = relationship("User")

class ItemCategory(TenantMixin,Base):
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    name = Column(String(100), nullable=False)
    category_type = Column(Enum(ItemPerishableNonPerishable, name="item_category_type"), nullable=False)

    inventory_items = relationship("Inventory", back_populates="item_category" ,cascade="all,delete-orphan")
    user = relationship("User")

class InventoryTransaction(TenantMixin, Base):
    __tablename__ = "inventory_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_cost = Column(Numeric(10, 2))
    total_value = Column(Numeric(12, 2))
    reference_id = Column(String(100))
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batch = relationship("InventoryBatch", back_populates="transaction")
    inventory  = relationship("Inventory",back_populates="transactions")
    user = relationship("User", back_populates="transactions")
  
class InventoryAlert(TenantMixin,Base):
    __tablename__ = "inventory_alert"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    alert_type = Column(Enum(AlertType), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    priority = Column(String(20), default="medium")
    message = Column(Text, nullable=False)
    current_quantity = Column(Numeric(12, 3))
    threshold_value = Column(Numeric(12, 3))
    suggested_action = Column(Text)
    affected_dishes = Column(Text)
    alert_date = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


    inventory = relationship("Inventory",back_populates="alerts")
    batch = relationship("InventoryBatch")
    acknowledger = relationship("User")