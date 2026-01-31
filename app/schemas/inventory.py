# app/schemas/inventory.py
from pydantic import BaseModel , Field
from datetime import date, datetime
from typing import List, Optional, Literal
from enum import Enum
from uuid import UUID
class InventoryBase(BaseModel):
    name: str
    quantity: float
    unit: str
    item_category_id: int
    storage_location_id: int
    price_per_unit: float
    total_cost: float
    purchase_unit: str
    purchase_unit_size: int
    type: Optional[str] = ""
    expiry_life: Optional[date] = None
    shelf_life_in_days: Optional[int] = Field(None, ge=0)
    date_added: Optional[datetime] = None

class InventoryItemCreate(BaseModel):
    sku: Optional[str] = None
    name: str
    quantity: float
    unit: str
    item_category_id: int
    storage_location_id: int

    price_per_unit: Optional[float] = None
    total_cost: Optional[float] = None
    current_quantity:Optional[float] = 0.0
    purchase_unit: str
    purchase_unit_size: int
    type: Optional[str] = ""
    expiry_date: Optional[date] = None
    shelf_life_in_days: Optional[int] = Field(None, ge=0)
    date_added: Optional[datetime] = None
class InventoryRead(InventoryBase):
    id: int
    date_added: datetime

    class Config:
        from_attributes  = True  # <-- Important to read SQLAlchemy models

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
    name: str
    quantity: float
    unit: str
    price_per_unit: float
    total_cost: float
    date_added: datetime
    expiry_date: date | None
    
    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    success: bool
    message: str
    data: InventoryOut      

class InventoryListResponse(BaseModel):
    success: bool
    message: str
    data: List[InventoryOut]     



# class InventorySearch(BaseModel):
#     name: Optional[str] = None
#     type: Optional[str] = None
#     start_date: Optional[str] = None
#     end_date: Optional[str] = None

class ItemPerishableNonPerishable(str,Enum):
    PERISHABLE="perishable"
    NON_PERISHABLE="non_perishable"  

class ItemCategoryCreate(BaseModel):
    name: str
    category_type: str 
    tenant_id : UUID | None = None
    user_id : int

class ItemCategoryUpdate(BaseModel):
    name: Optional[str] = None
    category_type: Optional[ItemPerishableNonPerishable] = None

class ItemCategoryOut(BaseModel):
    id: int
    name: str
    category_type: str

    class Config:
        from_attributes  = True  
class ItemCategoryResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    data: ItemCategoryOut

               

