from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr,Field
from typing import Optional,Dict
from app.models.tenants import SubscriptionTier, TenantStatus
from app.models.users import UserRole

class SuperAdminCreate(BaseModel):
    full_name: str | None = None
    email: EmailStr
    password: str
    mobile_no: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str    


# class LoginResponse(BaseModel):
#     data: LoginData  

class TokenResponse(BaseModel):
    access_token:str
    token_type:str = "bearer"

class TenantSchema(BaseModel):
    tenant_id: UUID
    tenant_name: str
    subscription_tier: SubscriptionTier
    status: TenantStatus

    max_users: int
    max_storage_gb: int
    max_api_calls_per_day: int

    white_label_config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True  # REQUIRED for SQLAlchemy
    } 

class TenantResponse(BaseModel):
    tenant_id: UUID
    tenant_name: str
    subscription_tier: SubscriptionTier
    status: TenantStatus

    model_config = {
        "from_attributes": True
    }    

class TenantCreateWithUser(BaseModel):
    tenant_name: str                     
    subscription_tier: SubscriptionTier = SubscriptionTier.basic
    max_users: int = 10
    max_storage_gb: int = 5
    max_api_calls_per_day: int = 10000

    # First admin user
    admin_email: EmailStr
    admin_password: str
    mobile_no: str
    full_name: str




















































































































































































