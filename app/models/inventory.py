from sqlalchemy import  Column, Integer, String, DateTime, Boolean, Numeric,ForeignKey, Text, Date, CheckConstraint, Index, Enum,Float
from datetime import datetime
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.base import Base
from sqlalchemy.orm import relationship
from app.db.mixins import TenantMixin

class PerishableLifecycle(PyEnum):
    FRESH = "fresh"
    NEAR_EXPIRY = "near_expiry"
    EXPIRED = "expired"

class ItemPerishableNonPerishable(str,PyEnum):
    PERISHABLE="perishable"
    NON_PERISHABLE="non_perishable"    

class Inventory(TenantMixin,Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.id"),nullable=False)
    item_category_id = Column(Integer,ForeignKey("item_categories.id"),nullable=False)
    name = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    type = Column(String, default="")
    expiry_date = Column(Date)
    purchase_unit = Column(String, nullable=False)
    purchase_unit_size = Column(Integer, nullable=False)
    shelf_life_in_days = Column(Integer)
    is_active = Column(Boolean,default=True)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(),onupdate=func.now(),default=datetime.utcnow)


    storage_location = relationship("StorageLocation")
    batches = relationship("InventoryBatch" , back_populates="item", cascade="all,delete-orphan")
    item_category = relationship("ItemCategory", back_populates="inventory_items")
    
    def __repr__(self):
        return f"<Inventory(name={self.name}, quantity={self.quantity} {self.unit})>"
    

class InventoryBatch(TenantMixin,Base):
    __tablename__ = "inventory_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
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
    
    # Relationships - tenant inherited from TenantMixin
    item = relationship("Inventory", back_populates="batches")
    # transactions = relationship("InventoryTransaction", back_populates="batch")
    
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
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    storage_location_id = Column(Integer,ForeignKey("storage_locations.id", ondelete="CASCADE"),nullable=True)
    name = Column(String,index=True,nullable=False)

    inventory_items = relationship("Inventory")

class StorageLocation(TenantMixin,Base):
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    storage_temp_min = Column(Numeric(5, 2))
    storage_temp_max = Column(Numeric(5, 2))
    is_active = Column(Boolean, default=True)

class ItemCategory(TenantMixin,Base):
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category_type = Column(Enum(ItemPerishableNonPerishable, name="item_category_type",native_enum=True,create_constraint=False,validate_strings=True), nullable=False)

    inventory_items = relationship("Inventory", back_populates="item_category" ,cascade="all,delete-orphan")