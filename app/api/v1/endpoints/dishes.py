"""
app/api/v1/endpoints/dishes.py
Dish management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models.dish import Dish, DishIngredient, DishType
from app.models.inventory import Inventory
from app.schemas.dish import AddDishRequest,DishOut,DishIngredientOut, DishUpdate
# from app.services.dish_service import DishService

router = APIRouter()

@router.post("/add_dish")
def add_dish(request: AddDishRequest, db: Session = Depends(get_db)):
    # Check if dish with same name exists
    existing_dish = db.query(Dish).filter(Dish.name == request.name).first()
    if existing_dish:
        raise HTTPException(status_code=400, detail="Dish with this name already exists.")

    # Get or create DishType
    dish_type = db.query(DishType).filter(DishType.name == request.type).first()
    if not dish_type:
        dish_type = DishType(name=request.type)
        db.add(dish_type)
        db.commit()
        db.refresh(dish_type)

    # Create new dish
    new_dish = Dish(name=request.name, type_id=dish_type.id)
    db.add(new_dish)
    db.commit()
    db.refresh(new_dish)

    # Process ingredients
    for ing in request.ingredients:
        unit = getattr(ing, "unit", "gm")
        cost_per_unit = getattr(ing, "cost_per_unit", 0.0)
        dish_ingredient = DishIngredient(
            dish_id=new_dish.id,
            ingredient_name=ing.name,
            quantity_required=ing.quantity_required,
            unit=unit,
            cost_per_unit=cost_per_unit
        )
        db.add(dish_ingredient)

    db.commit()
    return {"message": f"Dish '{request.name}' added successfully with ingredients."}


@router.get("/dishes", response_model=List[DishOut])
def list_dishes(db: Session = Depends(get_db)):
    dishes = db.query(Dish).all()
    result = []

    for dish in dishes:
        # Get the dish type name
        dish_type = db.query(DishType).filter(DishType.id == dish.type_id).first()

        # Get all ingredients for this dish
        ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()

        # Convert DishIngredient DB entries to response models
        ingredient_list = [
            DishIngredientOut(
                ingredient_name=di.ingredient_name,
                quantity_required=di.quantity_required,
                unit=di.unit,
                cost_per_unit=di.cost_per_unit
            )
            for di in ingredients if di.ingredient_name is not None
        ]

        # Append formatted dish to result
        result.append(DishOut(
            id=dish.id,
            name=dish.name,
            type=dish_type.name if dish_type else "Unknown",
            ingredients=ingredient_list
        ))

    return result


@router.get("/dishes/by_name", response_model=List[DishOut])
def search_dishes_by_name(partial_name: str, db: Session = Depends(get_db)):
    matched_dishes = db.query(Dish).filter(
        Dish.name.ilike(f"%{partial_name}%")
    ).all()

    if not matched_dishes:
        raise HTTPException(status_code=404, detail="No matching dishes found")

    result = []
    for dish in matched_dishes:
        dish_type = db.query(DishType).filter(DishType.id == dish.type_id).first()
        ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()

        ingredient_list = [
            DishIngredientOut(
                ingredient_name=di.ingredient_name,
                quantity_required=di.quantity_required,
                unit=di.unit,
                cost_per_unit=di.cost_per_unit
            )
            for di in ingredients if di.ingredient_name is not None
        ]

        result.append(DishOut(
            id=dish.id,
            name=dish.name,
            type=dish_type.name if dish_type else "Unknown",
            ingredients=ingredient_list
        ))

    return result


@router.delete("/dishes/{dish_name}")
def delete_dish_by_name(
    dish_name: str,
    confirm: bool = Query(False, description="Set to true to confirm deletion"),
    db: Session = Depends(get_db)
):
    dish = db.query(Dish).filter(Dish.name.ilike(dish_name)).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail=f"Deletion not confirmed. To delete dish '{dish.name}', set confirm=true."
        )

    db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).delete()
    db.delete(dish)
    db.commit()
    return {"message": f"Dish '{dish.name}' deleted successfully"}

@router.get("/dish_types")
def get_dish_types(db: Session = Depends(get_db)):
    dish_types = db.query(DishType).all()
    return [dt.name for dt in dish_types]

@router.get("/dishes/{dish_id}/cost")
def get_dish_cost(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()
    total_cost = 0.0
    ingredient_costs = []

    for di in ingredients:
        # Get the most recent inventory item for this ingredient
        inventory_item = db.query(Inventory).filter(
            Inventory.name.ilike(di.ingredient_name)
        ).order_by(Inventory.date_added.desc()).first()

        print(di.ingredient_name,"INGREDINETS")

        if not inventory_item:
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient '{di.ingredient_name}' not found in inventory"
            )
        print(di.ingredient_name,"INGREDIENT NAME")

        item_cost = di.quantity_required * inventory_item.price_per_unit
        total_cost += item_cost

        ingredient_costs.append({
            "ingredient": di.ingredient_name,
            "quantity_required": di.quantity_required,
            "unit_price": inventory_item.price_per_unit,
            "total_cost": item_cost
        })

    return {
        "dish_id": dish.id,
        "dish_name": dish.name,
        "ingredient_breakdown": ingredient_costs,
        "total_cost": round(total_cost, 2)
    }


@router.put("/dishes/{dish_id}")
def update_dish(dish_id: int, payload: DishUpdate, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    # Update dish name and type
    dish.name = payload.name

    # Lookup or create dish type
    dish_type = db.query(DishType).filter(DishType.name.ilike(payload.type)).first()
    if not dish_type:
        dish_type = DishType(name=payload.type)
        db.add(dish_type)
        db.commit()
        db.refresh(dish_type)
    dish.type_id = dish_type.id
    db.commit()

    # Fetch existing ingredients
    dish_ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()
    existing_ingredients = {di.ingredient_name.lower(): di for di in dish_ingredients}
    updated_names = {ing.ingredient_name.lower() for ing in payload.ingredients}

    for ing in payload.ingredients:
        key = ing.ingredient_name.lower()
        unit = getattr(ing, "unit", "gm")
        cost_per_unit = getattr(ing, "cost_per_unit", 0.0)
        if key in existing_ingredients:
            existing_ingredients[key].quantity_required = ing.quantity_required
            existing_ingredients[key].unit = unit
            existing_ingredients[key].cost_per_unit = cost_per_unit
        else:
            db.add(DishIngredient(
                dish_id=dish.id,
                ingredient_name=ing.ingredient_name,
                quantity_required=ing.quantity_required,
                unit=unit,
                cost_per_unit=cost_per_unit
            ))

    # Delete ingredients no longer in request
    for key, di in existing_ingredients.items():
        if key not in updated_names:
            db.delete(di)

    db.commit()
    return {"message": "Dish updated successfully"}