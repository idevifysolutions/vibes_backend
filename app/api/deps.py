"""
app/api/deps.py
Common dependencies for API routes
"""
from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from fastapi import Depends, HTTPException
from app.db.tenant import set_tenant ,get_current_tenant


def get_db() -> Generator:
    """
    Database session dependency
    
    Usage in routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_tenant(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Database session with automatic tenant context
    Combines application + database level security
    """
    # Set PostgreSQL RLS variable
    set_tenant(db, tenant_id)
    
    return db        

