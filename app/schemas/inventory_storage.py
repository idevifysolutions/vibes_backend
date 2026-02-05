from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Text

class StorageLocationBase(BaseModel):
    name: str
    storage_temp_min: Optional[Decimal] = Field(
        None, ge=-999.99, le=999.99
    )
    storage_temp_max: Optional[Decimal] = Field(
        None, ge=-999.99, le=999.99
    )
    tenant_id: UUID | None = None
    special_handling_instructions: Optional[str] = None
    
class StorageLocationCreate(StorageLocationBase):
    pass

class StorageLocationUpdate(StorageLocationBase):
    is_active: Optional[bool] = None

class StorageLocationResponse(StorageLocationBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True
