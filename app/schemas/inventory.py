# app/schemas/inventory.py
from pydantic import BaseModel , Field
from datetime import datetime
from typing import Optional

class InventoryBase(BaseModel):
    name: str
    quantity: float
    unit: str
    price_per_unit: float
    total_cost: float
    type: Optional[str] = ""

class InventoryItemCreate(BaseModel):
    name: str
    quantity: float
    unit: str
    price_per_unit: Optional[float] = None
    total_cost: Optional[float] = None
    type: Optional[str] = None
    date_added: Optional[datetime] = None
    
class InventoryRead(InventoryBase):
    id: int
    date_added: datetime

    class Config:
        orm_mode = True  # <-- Important to read SQLAlchemy models

class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None
    total_cost: Optional[float] = None
    type: Optional[str] = None


# """
# app/schemas/inventory.py
# Pydantic schemas for inventory
# """
# from pydantic import BaseModel, Field
# from typing import Optional
# from datetime import datetime


# class InventoryBase(BaseModel):
#     name: str = Field(..., min_length=1, max_length=200)
#     quantity: float = Field(..., gt=0)
#     unit: str = Field(..., min_length=1, max_length=50)
#     type: Optional[str] = Field(default="", max_length=100)


# class InventoryCreate(InventoryBase):
#     price_per_unit: Optional[float] = Field(None, ge=0)
#     total_cost: Optional[float] = Field(None, ge=0)
#     date_added: Optional[datetime] = None


class InventoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    price_per_unit: Optional[float] = Field(None, ge=0)
    total_cost: Optional[float] = Field(None, ge=0)
    type: Optional[str] = Field(None, max_length=100)
    date_added: Optional[datetime] = None


class InventoryOut(InventoryBase):
    id: int
    price_per_unit: float
    total_cost: float
    date_added: datetime
    
    class Config:
        from_attributes = True


# class InventorySearch(BaseModel):
#     name: Optional[str] = None
#     type: Optional[str] = None
#     start_date: Optional[str] = None
#     end_date: Optional[str] = None