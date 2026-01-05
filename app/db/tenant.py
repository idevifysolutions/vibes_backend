# from sqlalchemy import text
# from sqlalchemy.orm import Session

# def set_tenant(session: Session , tenant_id: str):
#     session.execute(
#         text("SET LOCAL app.current_tenant = :tenant_id"),
#         {"tenant_id": tenant_id}
#     )

"""
PostgreSQL Row-Level Security helper functions
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

def set_tenant(session: Session, tenant_id: int):
    """
    Set current tenant in PostgreSQL session variable
    """
    session.execute(
        text("SET LOCAL app.current_tenant = :tenant_id"),
        {"tenant_id": str(tenant_id)}
    )

def get_current_tenant(session: Session) -> int:
    """Get current tenant from session variable"""
    result = session.execute(
        text("SELECT current_setting('app.current_tenant', true)")
    )
    return int(result.scalar() or 0)

def clear_tenant(session: Session):
    """Clear tenant context"""
    session.execute(text("RESET app.current_tenant"))