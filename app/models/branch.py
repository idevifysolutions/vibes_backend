import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from datetime import datetime


class Branch(Base):
    __tablename__ = "branches"

    branch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)

    branch_name = Column(String(200), nullable=False)
    address = Column(String)
    contact_phone = Column(String(20))
    contact_email = Column(String(100))
    timezone = Column(String(50))

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
