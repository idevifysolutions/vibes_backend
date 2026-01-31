from sqlalchemy import  Column, Integer, String, DateTime, Boolean, Numeric,ForeignKey, Text, Date, CheckConstraint, Index, Enum,Float
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.base import Base
from sqlalchemy.orm import relationship
from app.db.mixins import TenantMixin
from sqlalchemy.dialects.postgresql import UUID

class UserRole(str,PyEnum):
    SUPER_ADMIN = "super_admin"
    BRANCH_MANAGER = "branch_manager"
    KITCHEN_MANAGER = "kitchen_manager"
    INVENTORY_CLERK = "inventory_clerk"
    CHEF_COOK = "chef_cook"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"

class User(TenantMixin,Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mobile_no = Column(String(15), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(Enum(UserRole,values_callable=lambda enum:[e.value for e in enum],native_enum=False),nullable=False)
    is_active = Column(Boolean, default=True)
    is_2fa_enabled = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime(timezone=True))
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=True,  # nullable=True only for Super Admin
        index=True
    )
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="users")
    branch_access = relationship("UserBranchAccess", back_populates="user")
    transactions = relationship("InventoryTransaction", back_populates="user")
    # adjustments = relationship("InventoryAdjustment", back_populates="user")

class UserBranchAccess(TenantMixin, Base):
    __tablename__ = "user_branch_access"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id", ondelete="CASCADE"), nullable=False)
    can_read = Column(Boolean, default=True)
    can_create = Column(Boolean, default=False)
    can_update = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="branch_access")
    branch = relationship("Branch")
    
    __table_args__ = (
        Index("idx_user_branch_tenant", "tenant_id", "user_id", "branch_id", unique=True),
    )