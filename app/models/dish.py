from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Float, ForeignKey,Enum, Text
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import TenantMixin
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class PreparationStatus(str,PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class PreparationBatchStatus(str,PyEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class OrderSource(PyEnum):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    ZOMATO = "zomato"
    SWIGGY = "swiggy"
    UBER_EATS = "uber_eats"
    OTHER_DELIVERY = "other_delivery"

class PrePreparedProductType(str, PyEnum):
    BATTER = "BATTER"          
    SAUCE = "SAUCE"             
    PASTE = "PASTE"            
    STOCK = "STOCK"             
    SPICES = "SPICES"                
    DOUGH = "DOUGH"              
    FILLING = "FILLING"        
    GRAVY = "GRAVY"             
    OTHER = "OTHER"    

class DishType(TenantMixin,Base): # veg or non-veg
    __tablename__ = "dish_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Dish(TenantMixin,Base):  # dishname
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type_id = Column(Integer, ForeignKey("dish_types.id"))
    standard_portion_size = Column(String(50))
    yield_quantity = Column(Numeric(8, 2))
    # preparation_method = Column(Text)
    preparation_time_minutes = Column(Integer)
    selling_price = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    type = relationship("DishType", backref="dishes")
    dish_ingredient = relationship("DishIngredient",back_populates="dish",cascade="all, delete-orphan")
    sales = relationship( "DishSale",back_populates="dish",cascade="all, delete-orphan" )
    wastage = relationship("Wastage",back_populates="dish",cascade="all, delete-orphan")

class DishIngredient(TenantMixin,Base): # it will track ingredients use in dish
    __tablename__ = "dish_ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"))
    preprepred_material_id = Column(UUID, ForeignKey("pre_prepared_dish_preparation.id"), nullable=True)
    is_semi_finished = Column(Boolean, default=False)
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
    semi_finished_product = relationship("PrePreparedMaterial")

class DishSale(TenantMixin, Base):
    __tablename__ = "dish_sales"

    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=True)
    quantity_sold = Column(Numeric(8, 2), nullable=True)
    unit_price = Column(Numeric(10, 2))
    total_amount = Column(Numeric(12, 2))
    order_source = Column(Enum(OrderSource), nullable=True)
    order_reference = Column(String(100))
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dish = relationship("Dish", back_populates="sales")

class DishPreparationBatch(TenantMixin,Base):
    __tablename__ = "dish_preparation_batches"

    id = Column(Integer,primary_key=True, index=True)
    batch_number = Column(String(100),unique=True, nullable=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    status = Column(Enum(PreparationBatchStatus), default=PreparationBatchStatus.IN_PROGRESS)
    total_dishes_planned = Column(Integer, default=0)
    total_dishes_completed = Column(Integer,default=0)
    total_cost = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    preparation_logs = relationship("DishPreparationBatchLog", back_populates="preparation_batch")

class DishPreparationBatchLog(TenantMixin, Base):  #dishpreparationlogs table
    """Track individual dish preparation events"""
    __tablename__ = "dish_preparation_batch_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("dish_preparation_batches.id", ondelete="CASCADE"), nullable=True, index=True)
    quantity_prepared = Column(Integer, nullable=True)
    track_status =  Column(Enum(PreparationBatchStatus), default=PreparationBatchStatus.IN_PROGRESS)
    preparation_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    notes = Column(String, nullable=True)
    total_cost = Column(Numeric(10, 2), default=0)
    inventory_deducted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    dish = relationship("Dish")
    user = relationship("User")
    preparation_batch = relationship("DishPreparationBatch", back_populates="preparation_logs")
    ingredient_consumptions_history = relationship("PreparationIngredientHistory", back_populates="preparation_log")
class PreparationIngredientHistory(TenantMixin, Base):
    """Track ingredient consumption per preparation"""
    __tablename__ = "preparation_ingredient_history"
    
    id = Column(Integer, primary_key=True, index=True)
    preparation_log_id = Column(Integer, ForeignKey("dish_preparation_batch_logs.id", ondelete="CASCADE"), nullable=True)
    ingredient_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id"), nullable=True)
    ingredient_name = Column(String, nullable=True)
    preprepred_material_id = Column(UUID, ForeignKey("pre_prepared_dish_preparation.id"), nullable=True)
    batch_number = Column(String(100), nullable=True)
    quantity_consumed = Column(Numeric(12, 3), nullable=True)
    unit = Column(String, nullable=True)
    cost_per_unit = Column(Numeric(10, 2), default=0)
    total_cost = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    preparation_log = relationship("DishPreparationBatchLog", back_populates="ingredient_consumptions_history")
    ingredient = relationship("Inventory")
    batch = relationship("InventoryBatch")

class PrePreparedMaterial(TenantMixin, Base): 
    __tablename__ = "pre_prepared_dish_preparation"

    id= Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255),nullable=True, index=True)
    storage_location_id = Column(Integer,ForeignKey("storage_locations.id", ondelete="CASCADE"),nullable=True)
    product_type = Column(Enum(PrePreparedProductType),nullable=True) 
    description = Column(Text, nullable=True)
    unit = Column(String(20), default="gm")
    shelf_life_hours = Column(Integer, nullable=True)
    preparation_time_minutes = Column(Integer, nullable=True)
    yield_quantity = Column(Numeric(12,3),nullable=True)
    cost_per_unit = Column(Numeric(10,2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


    ingredients = relationship("IngredientForPrePreparedIngredients", back_populates="semi_finished_product", cascade="all, delete-orphan")
    stock_batches = relationship("PrePreparedMaterialStock", back_populates="product", cascade="all, delete-orphan")

class IngredientForPrePreparedIngredients(TenantMixin, Base):
    """Raw ingredients needed to make semi-finished product"""
    __tablename__ = "ingredients_for_pre_prepared_ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    semi_finished_product_id = Column(UUID, ForeignKey("pre_prepared_dish_preparation.id", ondelete="CASCADE"), nullable=True)
    ingredient_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    inventory_transaction_id = Column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id", ondelete="CASCADE"), nullable=True)
    quantity_required = Column(Numeric(12, 3), nullable=True)
    ingredient_name = Column(String(255), nullable=True)
    unit = Column(String(20), default="gm")
    cost_per_unit = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    semi_finished_product = relationship("PrePreparedMaterial", back_populates="ingredients")
    ingredient = relationship("Inventory")    

class PrePreparedMaterialStock(TenantMixin, Base):
    """Stock/batches of prepared semi-finished products"""
    __tablename__ = "pre_prepared_material_stock"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("pre_prepared_dish_preparation.id", ondelete="CASCADE"), nullable=True)
    batch_number = Column(String(100), nullable=True, index=True)
    quantity_produced = Column(Numeric(12, 3), nullable=True)
    quantity_remaining = Column(Numeric(12, 3), nullable=True)
    unit = Column(String(20), default="gm")
    production_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    preparation_log_id = Column(Integer, nullable=True)
    total_cost = Column(Numeric(12, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    product = relationship("PrePreparedMaterial", back_populates="stock_batches")
    user = relationship("User")    