from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

class StorageLocationBase(BaseModel):
    name: str
    storage_temp_min: Optional[Decimal] = Field(
        None, ge=-999.99, le=999.99
    )
    storage_temp_max: Optional[Decimal] = Field(
        None, ge=-999.99, le=999.99
    )
    
class StorageLocationCreate(StorageLocationBase):
    pass

class StorageLocationUpdate(StorageLocationBase):
    is_active: Optional[bool] = None

class StorageLocationResponse(StorageLocationBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True
