from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Float, ForeignKey,Enum
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import TenantMixin
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class OrderSource(PyEnum):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    ZOMATO = "zomato"
    SWIGGY = "swiggy"
    UBER_EATS = "uber_eats"
    OTHER_DELIVERY = "other_delivery"
class DishType(TenantMixin,Base):
    __tablename__ = "dish_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Dish(TenantMixin,Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type_id = Column(Integer, ForeignKey("dish_types.id"))
    standard_portion_size = Column(String(50))
    yield_quantity = Column(Numeric(8, 2))
    preparation_time_minutes = Column(Integer)
    selling_price = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    type = relationship("DishType", backref="dishes")
    dish_ingredient = relationship("DishIngredient",back_populates="dish",cascade="all, delete-orphan")
    preparations = relationship(
        "DishPreparation",
        back_populates="dish",
        cascade="all, delete-orphan"
    )
    sales = relationship( "DishSale",back_populates="dish",cascade="all, delete-orphan" )
    wastage = relationship("Wastage",back_populates="dish",cascade="all, delete-orphan")

class DishIngredient(TenantMixin,Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    inventory_transaction_id = Column( UUID(as_uuid=True),  ForeignKey("inventory_transactions.id", ondelete="CASCADE"), nullable=True)
    quantity_required = Column(Float)
    ingredient_name = Column(String, index=True)
    unit = Column(String, default="gm")
    cost_per_unit = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dish = relationship("Dish", back_populates="dish_ingredient")
    inventory_item = relationship("Inventory")

class DishPreparation(TenantMixin, Base):
    __tablename__ = "dish_preparation"

    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    quantity_prepared = Column(Numeric(8, 2), nullable=False)
    preparation_date = Column(DateTime(timezone=True), server_default=func.now())
    prepared_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    dish = relationship("Dish", back_populates="preparations")
    prepared_by = relationship("User")


class DishSale(TenantMixin, Base):
    __tablename__ = "dish_sales"

    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    quantity_sold = Column(Numeric(8, 2), nullable=False)
    unit_price = Column(Numeric(10, 2))
    total_amount = Column(Numeric(12, 2))
    order_source = Column(Enum(OrderSource), nullable=False)
    order_reference = Column(String(100))
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dish = relationship("Dish", back_populates="sales")
