from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("inventory.id"))
    quantity_left = Column(Float)
    date = Column(DateTime, default=datetime.utcnow)

    ingredient = relationship("Inventory")
