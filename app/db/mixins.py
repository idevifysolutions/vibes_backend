from sqlalchemy import (
     Column, Integer, ForeignKey
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, Session, Query
import uuid 
from sqlalchemy.dialects.postgresql import UUID

class TenantMixin: 
    """ 
    Mixin to automatically add tenant_id to all tenant-aware tables. 
    Provides helper methods for tenant filtering. 
    """ 

    @declared_attr 
    def tenant_id(cls): 
        return Column( 
            UUID(as_uuid=True),  
            ForeignKey("tenants.tenant_id", ondelete="CASCADE"),  
            nullable=False,  
            index=True 
        ) 

    @declared_attr 
    def tenant(cls): 
        return relationship("Tenant") 

    @classmethod
    def get_for_tenant(cls, session: Session, tenant_id: UUID):
        if tenant_id is None:
            raise ValueError("tenant_id required tenat-scoped query")
        return session.query(cls).filter(cls.tenant_id == tenant_id)
 
    @classmethod 
    def create_for_tenant(cls, tenant_id: UUID, **kwargs): 
        """Create instance with tenant_id"""
        if tenant_id is None:
            raise ValueError("tenant_id is required")

        obj = cls(tenant_id=tenant_id, **kwargs)
        Session.add(obj)
        return obj    

    @classmethod
    def for_super_admin(cls, session: Session):
        return session.query(cls)         


#Prevent accidental cross-tenant inserts:

# @event.listens_for(Session, "before_flush")
# def validate_tenant(session, flush_context, instances):
#     for obj in session.new:
#         if isinstance(obj, TenantMixin) and obj.tenant_id is None:
#             raise RuntimeError("Tenant-aware model created without tenant_id")
