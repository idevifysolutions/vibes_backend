from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import TenantMixin

class DishType(TenantMixin,Base):
    __tablename__ = "dish_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Dish(TenantMixin,Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type_id = Column(Integer, ForeignKey("dish_types.id"))

    type = relationship("DishType", backref="dishes")
    dishingredient = relationship("DishIngredient",back_populates="dish")

class DishIngredient(TenantMixin,Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    ingredient_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    quantity_required = Column(Float)
    ingredient_name = Column(String, index=True)
    unit = Column(String, default="gm")
    cost_per_unit = Column(Float, default=0.0)

    dish = relationship("Dish", back_populates="dishingredient")