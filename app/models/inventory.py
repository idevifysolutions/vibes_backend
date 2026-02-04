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
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    EXPIRY_WARNING = "EXPIRY_WARNING"
    BATCH_TYPE = "BATCH_TYPE" 

class AlertStatus(PyEnum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SNOOZED = "SNOOZED"   

class UnitType(str, PyEnum):
    KILOGRAM = "kg"
    GRAM = "gm"
    MILLIGRAM = "mg"
    LITER = "liter"
    MILLILITER = "ml"

AlertTypeEnum = Enum(
    AlertType,
    name="alerttype",
    create_type=False,
)

AlertStatusEnum = Enum(
    AlertStatus,
    name="alertstatus",
    values_callable=lambda enum: [e.value for e in enum],
    create_type=False,
)
class Inventory(TenantMixin,Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.id"),nullable=True)
    item_category_id = Column(Integer,ForeignKey("item_categories.id"),nullable=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    name = Column(String, index=True, nullable=True)
    sku = Column(String(100), unique=True ,nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(
        Enum(
            UnitType,
            name="unittype",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=True,
    )
    price_per_unit = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    type = Column(String, default="")
    expiry_date = Column(Date)
    purchase_unit =  Column(
        Enum(
            UnitType,
            name="unittype",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=True,
    )
    purchase_unit_size = Column(Integer, nullable=True)
    shelf_life_in_days = Column(Integer)
    reorder_point = Column(Numeric(12, 3), nullable=True)
    reorder_quantity = Column(Numeric(12, 3),nullable=True)
    unit_cost = Column(Numeric(10, 2),nullable=True)
    expiry_alert_threshold_days = Column(Integer, default=3)
    fresh_threshold_days = Column(Integer, default=3)
    near_expiry_threshold_days = Column(Integer, default=1)
    current_quantity = Column(Numeric(12, 3), default=0)
    is_active = Column(Boolean,default=True)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=True)
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
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(Date)
    unit = Column(
        Enum(
            UnitType,
            name="unittype",
            native_enum=True,
            validate_strings=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
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
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=True)
    storage_location_id = Column(Integer,ForeignKey("storage_locations.id", ondelete="CASCADE"),nullable=True)
    name = Column(String,index=True,nullable=True)

    inventory_item = relationship("Inventory")
    user = relationship("User")

class StorageLocation(TenantMixin,Base):
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    name = Column(String(100), nullable=True)
    storage_temp_min = Column(Numeric(5, 2))
    storage_temp_max = Column(Numeric(5, 2))
    special_handling_instructions = Column(Text)
    is_active = Column(Boolean, default=True)

    user = relationship("User")
class ItemCategory(TenantMixin,Base):
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    name = Column(String(100), nullable=True)
    category_type = Column(Enum(ItemPerishableNonPerishable, name="item_category_type"), nullable=True)

    inventory_items = relationship("Inventory", back_populates="item_category" ,cascade="all,delete-orphan")
    user = relationship("User")
class InventoryTransaction(TenantMixin, Base):
    __tablename__ = "inventory_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    transaction_type = Column(Enum(TransactionType), nullable=True)
    quantity = Column(Numeric(12, 3), nullable=True)
    unit_cost = Column(Numeric(10, 2))
    total_value = Column(Numeric(12, 2))
    reference_id = Column(String(100))
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())
    dish_ingredient_id = Column(Integer,ForeignKey("dish_ingredients.id", ondelete="SET NULL"),nullable=True)
    pre_prepared_material_id = Column(UUID,ForeignKey("pre_prepared_dish_preparation.id",ondelete="SET NULL"),nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batch = relationship("InventoryBatch", back_populates="transaction")
    inventory  = relationship("Inventory",back_populates="transactions")
    user = relationship("User", back_populates="transactions")
    dish_ingredient = relationship("DishIngredient", foreign_keys=[dish_ingredient_id])
    pre_prepare_product = relationship("PrePreparedMaterial", foreign_keys=[pre_prepared_material_id])
  
class InventoryAlert(TenantMixin,Base):
    __tablename__ = "inventory_alert"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    alert_type = Column(
        AlertTypeEnum,
        nullable=True
    )
    status = Column(AlertStatusEnum, default=AlertStatus.ACTIVE)
    priority = Column(String(20), default="medium")
    message = Column(Text, nullable=True)
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

class AlertConfiguration(TenantMixin, Base):
    __tablename__ = "alert_configurations"
    
    id = Column(Integer, primary_key=True)
    item_category_id = Column(Integer, ForeignKey("item_categories.id"))
    alert_type = Column(AlertTypeEnum, nullable=True)
    threshold_value = Column(Integer)  # days for expiry, quantity for stock
    lead_time_days = Column(Integer)  # for expiry alerts
    notification_channels = Column(String)  # JSON: ["email", "sms", "in_app"]
    recipient_user_ids = Column(String)  
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    item_category = relationship("ItemCategory") 

class AlertNotification(TenantMixin, Base):
    __tablename__ = "alert_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID, ForeignKey("inventory_alert.id", ondelete="CASCADE"))
    channel = Column(String(20))  # email, sms, in_app
    recipient_user_id = Column(Integer, ForeignKey("users.id"))
    recipient_contact = Column(String)  # email address or phone number
    status = Column(String(20))  # sent, failed, pending
    sent_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    alert = relationship("InventoryAlert")
    recipient = relationship("User")       