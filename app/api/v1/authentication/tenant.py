from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.tenants import Tenant
from app.models.users import User, UserRole
from app.schemas.superadmin import TenantCreateWithUser, TenantSchema,TenantResponse
from app.utils.auth_helper import hash_password, require_super_admin
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


router = APIRouter()

def create_tenant_with_admin(db: Session, payload: TenantCreateWithUser):
    try:
    # Check if tenant already exists
        existing_tenant = db.query(Tenant).filter(Tenant.tenant_name == payload.tenant_name).first()
        if existing_tenant:
            raise HTTPException(status_code=400, detail="Tenant already exists")

        # Create tenant
        tenant = Tenant(
            tenant_name=payload.tenant_name,
            subscription_tier=payload.subscription_tier,
            max_users=payload.max_users,
            max_storage_gb=payload.max_storage_gb,
            max_api_calls_per_day=payload.max_api_calls_per_day,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        admin_user = User(
            email=payload.admin_email,
            hashed_password=hash_password(payload.admin_password),
            mobile_no=payload.mobile_no,
            full_name=payload.full_name,
            role=UserRole.BRANCH_MANAGER,  
            tenant=tenant
        )
        db.add(tenant)
        db.add(admin_user)

        db.commit()

        db.refresh(tenant)
        db.refresh(admin_user)
    
        return {
            "data": {
                "status": status.HTTP_201_CREATED,
                "message": "Tenant and admin created successfully",
                "tenant": {
                    "tenant_id": tenant.tenant_id,
                    "tenant_name": tenant.tenant_name,
                    "admin_user_id": admin_user.id,
                    "admin_email": admin_user.email,
                }
            }
        }
    except HTTPException:
        # Business / validation errors
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant or admin already exists"
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant and admin"
        )

@router.post("/create-with-admin")
def create_tenant(
    payload: TenantCreateWithUser,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin), 
):
    return create_tenant_with_admin(db, payload)
