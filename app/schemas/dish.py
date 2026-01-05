from pydantic import BaseModel
from typing import List, Optional

class IngredientInput(BaseModel):
    name: str
    quantity_required: float
    unit: str = "gm"


class AddDishRequest(BaseModel):
    name: str
    type: str
    ingredients: List[IngredientInput]


class DishIngredientOut(BaseModel):
    ingredient_name: str
    quantity_required: float
    unit: str = "gm"
    cost_per_unit: float = 0.0


class DishOut(BaseModel):
    id: int
    name: str
    type: str
    ingredients: List[DishIngredientOut]

    class Config:
        orm_mode = True


class DishIngredientUpdate(BaseModel):
    ingredient_name: str
    quantity_required: float
    unit: str = "gm"  # Default unit


class DishUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    ingredients: Optional[List[DishIngredientUpdate]] = None

