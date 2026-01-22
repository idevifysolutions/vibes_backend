from typing import Generic, TypeVar, Optional
from pydantic.generics import GenericModel

T = TypeVar("T")

class ApiResponse(GenericModel, Generic[T]):
    success: bool
    status_code: int
    message: str
    data: Optional[T]
