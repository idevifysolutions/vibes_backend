import re
from passlib.context import CryptContext
import hashlib
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.core.config import settings
from jose import jwt ,JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.users import User, UserRole

security = HTTPBearer()

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


PASSWORD_REGEX = re.compile(
    r"""
    ^(?=.*[a-z])        # lowercase
     (?=.*[A-Z])        # uppercase
     (?=.*\d)           # digit
     (?=.*[@$!%*?&])    # special char
     [A-Za-z\d@$!%*?&]{8,}$
    """,
    re.VERBOSE,
)

def validate_password(password: str) -> None:
    if not PASSWORD_REGEX.match(password):
        raise ValueError(
             "Password must be at least 8 characters long and include "
            "uppercase, lowercase, number, and special character."
        )
    
def hash_password(password:str) -> str:
    # digest = hashlib.sha256(password.encode("utf-8")).digest()
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    # digest = hashlib.sha256(password.encode("utf-8")).digest()
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp":expire, "type":"access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
#Extract a Bearer token from the Authorization header using the OAuth2 standard

token_authorization = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
(token_authorization,"TOKEN")

def get_current_user(
   credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    print("RAW TOKEN", token)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
    except JWTError:
        raise HTTPException(status_code=401,detail="Invalid Token")   

    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User Not Found") 
    
    return user
     
def require_super_admin(
        current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user

def require_authenticated_user(
    current_user: User = Depends(get_current_user)
):
    return current_user

def require_tenant_user(
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required"
        )
    return current_user

def get_tanant_scope(
    current_user: User,
    requested_tenant_id: UUID | None = None
) -> UUID:
   
    if current_user.role == UserRole.SUPER_ADMIN:
        if not requested_tenant_id:
           raise HTTPException(
               status_code=400,
               detail="tenant_id is required for super admin"
           )
        return requested_tenant_id
    
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant access required"
        )
    
    if requested_tenant_id and requested_tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another tenant"
        )
    
    return current_user.tenant_id
   

#for production
# pwd_context = CryptContext(
#     schemes=["argon2"],
#     argon2__time_cost=3,
#     argon2__memory_cost=65536,  # 64 MB
#     argon2__parallelism=2,
# )