import uuid
from sqlalchemy import Column, String, Enum, Integer, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
from datetime import datetime
from sqlalchemy.orm import relationship

class SubscriptionTier(enum.Enum):
    basic = "basic"
    standard = "standard"
    premium = "premium"


class TenantStatus(enum.Enum):
    active = "active"
    suspended = "suspended"
    inactive = "inactive"


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_name = Column(String(200), nullable=True)

    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.basic)
    status = Column(Enum(TenantStatus), default=TenantStatus.active)

    max_users = Column(Integer, default=10)
    max_storage_gb = Column(Integer, default=5)
    max_api_calls_per_day = Column(Integer, default=10000)

    white_label_config = Column(JSON)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

    users = relationship("User",back_populates="tenant",cascade="all, delete-orphan")
