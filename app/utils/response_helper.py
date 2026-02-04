from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

def success_response(data, message: str, status_code: int = 200):
    return {
        "success": True,
        "status_code": status_code,
        "message": message,
        "data": data,
    }


def handle_db_exception(db: Session, e: Exception, message: str = "Operation failed"):
    db.rollback()

    print("ERROR TYPE:", type(e))
    print("ERROR MESSAGE:", e)

    if isinstance(e, IntegrityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{message} | ERROR: {str(e)}"
        )

    if isinstance(e, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{message} | DB ERROR: {str(e)}"
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{message} | UNEXPECTED ERROR: {str(e)}"
    )