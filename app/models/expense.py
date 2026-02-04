from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.base import Base
from app.db.mixins import TenantMixin


class Expense(TenantMixin,Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=True)
    
    def __repr__(self):
        return f"<Expense(item={self.item_name}, cost={self.total_cost})>"
