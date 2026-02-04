from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.common import ApiResponse
from app.schemas.superadmin import LoginData, SuperAdminCreate, TokenResponse,LoginRequest
from app.models import User, UserRole
from app.api.deps import get_db
from app.utils.auth_helper import create_access_token, validate_password,hash_password, verify_password
from sqlalchemy.exc import SQLAlchemyError
import logging

router = APIRouter()

MAX_FAILED_LOGIN_ATTEMPTS = 5

@router.post("/create-superadmin", status_code=status.HTTP_201_CREATED)
def create_super_admin(payload: SuperAdminCreate, db:Session = Depends(get_db)):

    existing_admin = db.query(User).filter(
        User.role == UserRole.SUPER_ADMIN
    ).first()

    print(UserRole.SUPER_ADMIN,"UserRole.SUPER_ADMIN")

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin already exists"
        )
    
    try:
        validate_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if db.query(User).filter(
        (User.email == payload.email) |
        (User.mobile_no == payload.mobile_no)
    ).first():
        raise HTTPException(
            status_code=400,
            detail="email already exists"
        )       

    super_admin = User(
        email=payload.email,
        mobile_no=payload.mobile_no,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_2fa_enabled=False,
        failed_login_attempts=0,
        tenant_id=None,
        is_super_admin=True
    )    

    db.add(super_admin)
    db.commit()
    db.refresh(super_admin)

    return {
       "data":{
            "status": status.HTTP_201_CREATED,
        "message":"Super Admin created succesfully",
        "email":super_admin.email,
        "role": super_admin.role
       }
    }


# @router.post("/superadmin/login", response_model=TokenResponse)
# def superadmin_login(
#     payload: LoginRequest,
#     db: Session = Depends(get_db),
# ):
#     user = (
#         db.query(User).filter(User.email == payload.email).first()
#     )

#     if not user or not verify_password(payload.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials",
#         )
    
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Inactive account"
#         )
    
#     if user.role != UserRole.SUPER_ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not a super admin",
#         )
    
#     access_token = create_access_token(
#         {
#             "sub":str(user.id),
#             "role":user.role.value,
#         }
#     )

#     return TokenResponse(access_token=access_token)

# for swagger authentication
@router.post("/login", response_model=ApiResponse[LoginData],status_code=status.HTTP_200_OK)
def superadmin_login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
    
            email = payload.email  #username == email
            print(email,"EMAIL")
            password = payload.password
            print(password,"PASSWORD")

            user = db.query(User).filter(User.email == email).first()

            print(user,"TEA")


            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is locked due to multiple failed login attempts"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Inactive account"
                )
            
            if not verify_password(password, user.hashed_password):
                user.failed_login_attempts += 1

                if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                    user.is_active = False

                db.commit()    

                remaining = max(
                    0, MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
                )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=(
                        "Invalid credentials"
                        if remaining == 0
                        else f"Invalid credentials. {remaining} attempts remaining"
                    ),
                )
            user.failed_login_attempts = 0
            user.last_login = datetime.utcnow()
            db.commit()
            
            access_token = create_access_token(
                {
                    "sub":str(user.id),
                    "role":user.role.value,
                    "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                    "type": "access",
                }
            )

            return {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Login successful",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "role": user.role.value
                    # "full_name":user.full_name,
                    # "email":user.email
               }
            }
    except HTTPException:
        # Re-raise known FastAPI errors
        raise

    except SQLAlchemyError as e:
        print(e,"PERINT")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to a server error"
        )
    # HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Login failed due to a server error"
    #     )

#unlock user
# @router.post("/users/{user_id}/unlock")
# def unlock_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     _: User = Depends(require_super_admin),
# ):
#     user = db.get(User, user_id)
#     if not user:
#         raise HTTPException(404, "User not found")

#     user.failed_login_attempts = 0
#     user.is_active = True
#     db.commit()

#     return {"detail": "User account unlocked"}


    