from enum import Enum as PyEnum
from sqlalchemy import  Column, Integer, String, DateTime, Boolean, Numeric,ForeignKey, Text, Date, CheckConstraint, Index, Enum,Float, func
from app.db.mixins import TenantMixin
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

class WastageReason(PyEnum):
    EXPIRY = "expiry"
    DAMAGE = "damage"
    CONTAMINATION = "contamination"
    UNSOLD_DISH = "unsold_dish"
    PREPARATION_ERROR = "preparation_error"
    SPILLAGE = "spillage"
    STAFF_MEAL = "staff_meal"
    SAMPLING = "sampling"
    OTHER = "other"


class WastageType(PyEnum):
    DISH = "dish"
    INVENTORY = "inventory"


class Wastage(TenantMixin,Base):
    __tablename__ = "wastage_management"

    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    wastage_type = Column(Enum(WastageType, nullable=False))
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"))
    inventory_item_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"))
    inventory_batch_id = Column(Integer, ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    quantity_wasted =  Column(Numeric(12, 3), nullable=False)
    unit_cost = Column(Numeric(12, 4), nullable=False)
    cost_value = Column(Numeric(12, 2), nullable=False)
    wastage_reason = Column(Enum(WastageReason), nullable=False)
    wastage_date = Column(DateTime(timezone=True), server_default=func.now())
    photo_url = Column(String(500))
    recorded_by_user_id = Column( Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dish = relationship("Dish", back_populates="wastage")
    inventory_item = relationship("Inventory")
    inventory_batch = relationship("InventoryBatch")
    recorded_by = relationship("User")


    # __table_args__ = (
    #     # Tenant indexes
    #     Index("idx_wastage_tenant", "tenant_id"),
    #     Index("idx_wastage_tenant_date", "tenant_id", "wastage_date"),
    #     Index("idx_wastage_tenant_type", "tenant_id", "wastage_type"),

    #     # Cost integrity
    #     CheckConstraint("quantity_wasted > 0", name="ck_wastage_qty_positive"),
    #     CheckConstraint("unit_cost >= 0", name="ck_wastage_unit_cost_positive"),
    #     CheckConstraint("cost_value = quantity_wasted * unit_cost",
    #                     name="ck_wastage_cost_calculated"),

    #     # Type safety
    #     CheckConstraint(
    #         """
    #         (wastage_type = 'dish' AND dish_id IS NOT NULL AND inventory_item_id IS NULL)
    #         OR
    #         (wastage_type = 'inventory' AND inventory_item_id IS NOT NULL)
    #         """,
    #         name="ck_wastage_type_target"
    #     ),
    # )