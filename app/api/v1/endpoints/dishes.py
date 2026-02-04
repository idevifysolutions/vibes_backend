"""
app/api/v1/endpoints/dishes.py
Dish management endpoints
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query,status
from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session,joinedload
from typing import List, Optional

from app.api.deps import get_db
from app.models.dish import Dish,DishType, DishIngredient, DishPreparationBatch , PrePreparedMaterial, PreparationBatchStatus,PreparationIngredientHistory,PrePreparedMaterialStock,IngredientForPrePreparedIngredients,DishPreparationBatchLog
from app.models.inventory import Inventory
from app.models.users import User
from app.schemas.dish import AvailableBatchesResponse, BatchDishPreparation, BatchInfo, BatchPreparationResult, BulkDishIngredientAdd,DishCreate, DishIngredientOut,DishIngredientResponse, DishIngredientType, DishOut, DishTypeCreate, DishTypeOut,DishTypeUpdate,DishUpdate,AddDishIngredient,PreparationResult, ProduceSemiFinished,SemiFinishedProductCreate, SingleDishPreparation
from app.services.dish_service import DishIngredientService, DishPreparationService, SemiFinishedService
from app.utils.auth_helper import get_current_user
from app.utils.response_helper import handle_db_exception
from uuid import UUID

router = APIRouter()

@router.post("/add_dish_type",status_code=status.HTTP_201_CREATED)
def add_dish_type(
    data: DishTypeCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    try:
        existing = db.query(DishType).filter(func.lower(DishType.name) == data.name.lower()).first()
        if existing:
            raise HTTPException(status_code=409, detail="Dish type with this name already exists.")

        obj = DishType(
            name=data.name,
            tenant_id=current_user.tenant_id
            )
        db.add(obj)
        db.commit()
        db.refresh(obj)
    
        return {
            "success": True,
            "message": "Dish type added successfully",
            "data": obj
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to create dish type")

@router.get("/get_dish_types",status_code=status.HTTP_200_OK )
def list_dish_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    try:
         data = db.query(DishType).order_by(DishType.id.asc()).all()

         return {
            "success": True,
            "message": "Dishes added successfully",
            "data": data
         }
    except Exception as e:
        handle_db_exception(db, e, "Failed to list dish types")


@router.put("/update_dish_types/{dish_type_id}", status_code=status.HTTP_200_OK)
def update_dish_type(
    dish_type_id: int, 
    data: DishTypeUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    
    try:
        obj = db.query(DishType).filter(DishType.id == dish_type_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Dish type not found.")

        if data.name:
            existing = (
                db.query(DishType)
                .filter(func.lower(DishType.name) == data.name.lower(), DishType.id != dish_type_id)
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="Dish type with this name already exists.")
            obj.name = data.name

        db.commit()
        db.refresh(obj)
        
        return {
            "data" :obj
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to update dish type")

@router.delete("/delete_dish_type/{dish_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish_type(
    dish_type_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)    
):
    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    try:
        obj = db.query(DishType).filter(DishType.id == dish_type_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Dish type not found.")

        in_use = db.query(Dish).filter(Dish.type_id == dish_type_id).first()
        if in_use:
            raise HTTPException(status_code=400, detail="Dish type is used by dishes.")

        db.delete(obj)
        db.commit()
        return {
                "success": True,
                "message": "Item category deleted successfully",
            }
    except HTTPException:
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to delete dish type")      


@router.post("/add_dish",status_code=status.HTTP_201_CREATED)
def create_dish(
    data: DishCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    try:
        dish_type = db.query(DishType).filter(DishType.id == data.type_id).first()
        if not dish_type:
            raise HTTPException(status_code=400, detail="Invalid type_id.")
        
        data = data.model_dump()
        data["tenant_id"] = current_user.tenant_id
        obj = Dish(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)

        dish = (db.query(Dish).options(joinedload(Dish.type)).filter(Dish.id == obj.id).first())
        return {
            "success" :True,
            "message":"Dish Added Successfully.",
            "data":dish,
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to create dish")    

@router.get("/dishes")
def list_dishes(
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user:User = Depends(get_current_user)
):
    
    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    try:
        data = db.query(Dish).options(joinedload(Dish.type))
        if is_active is not None:
            data = data.filter(Dish.is_active == is_active)
        response = data.all()

        return {
            "Success":True,
            "data":response
        }

    except Exception as e:
        handle_db_exception(db, e, "Failed to list dishes")              

@router.put("/update_dish/{dish_id}")
def update_dish(
    dish_id: int, 
    payload: DishUpdate, 
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    
    try:
        dish = db.query(Dish).filter(Dish.id == dish_id).first()
        if not dish:
           raise HTTPException(status_code=404, detail="Dish not found")
       
        if payload.type_id is not None:
            dish_type = db.query(DishType).filter(DishType.id == payload.type_id).first()
            if not dish_type:
                raise HTTPException(status_code=400, detail="Invalid type_id")
            dish.type_id = payload.type_id

        if payload.name is not None:
            dish.name = payload.name    
       
        if payload.standard_portion_size is not None:
            dish.standard_portion_size = payload.standard_portion_size 

        if payload.yield_quantity is not None:
            dish.yield_quantity = payload.yield_quantity

        if payload.preparation_time_minutes is not None:
            dish.preparation_time_minutes = payload.preparation_time_minutes

        if payload.selling_price is not None:
            dish.selling_price = payload.selling_price

        if payload.is_active is not None:
            dish.is_active = payload.is_active    

        db.commit()
        db.refresh(dish)

        updated_dish = (
                         db.query(Dish)
                         .options(joinedload(Dish.type))
                         .filter(Dish.id == dish_id)
                         .first()
                     ) 
        
        return {
                    "success": True,
                    "message": "Dish updated successfully",
                    "data": updated_dish
                }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to update dish")

@router.delete("/delete_dish/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(
    dish_id: int,
    db: Session = Depends(get_db),
    current_user:User =Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    
    try:
        obj = db.query(Dish).get(dish_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Dish not found.")

        db.delete(obj)
        db.commit()

        return {
            "Success":True,
            "Message":"Dish Deleted Successfully."
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_db_exception(db, e, "Failed to delete dish")        


# @router.get("/{dish_id}/ingredients/available-batches", response_model=AvailableBatchesResponse)
# def get_available_batches(
#     dish_id: int,
#     ingredient_id: int,
#     unit: str = "gm",
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user)
# ):
#     """
#     Get all available batches for an ingredient
#     Shows user which batches they can choose from with expiry warnings
#     """
    
#     # Verify dish exists
#     dish = db.query(Dish).filter(
#         and_(
#             Dish.tenant_id == current_user.tenant_id,
#             Dish.id == dish_id
#         )
#     ).first()
    
#     if not dish:
#         raise HTTPException(status_code=404, detail="Dish not found")
    
#     # Get ingredient info
#     ingredient = db.query(Inventory).filter(
#         and_(
#             Inventory.tenant_id == current_user.tenant_id,
#             Inventory.id == ingredient_id
#         )
#     ).first()
    
#     if not ingredient:
#         raise HTTPException(status_code=404, detail="Ingredient not found")
    
#     # Get all available batches
#     batches = DishIngredientService.get_available_batches_for_ingredient(
#         db=db,
#         tenant_id=current_user.tenant_id,
#         ingredient_id=ingredient_id,
#         unit=unit
#     )
    
#     # Count batch types
#     fresh_count = sum(1 for b in batches if not b.is_near_expiry and (not b.days_until_expiry or b.days_until_expiry > 7))
#     near_expiry_count = sum(1 for b in batches if b.is_near_expiry and b.days_until_expiry and b.days_until_expiry >= 0)
#     expired_count = sum(1 for b in batches if b.days_until_expiry and b.days_until_expiry < 0)
    
#     total_available = sum(float(b.quantity_remaining) for b in batches if not (b.days_until_expiry and b.days_until_expiry < 0))
    
#     # Generate warning message
#     warning = None
#     if expired_count > 0:
#         warning = f"{expired_count} batch(es) expired"
#     elif near_expiry_count > 0:
#         warning = f"{near_expiry_count} batch(es) expiring soon - use first!"
    
#     # Get recommended batch (first non-expired)
#     active_batches = [b for b in batches if not (b.days_until_expiry and b.days_until_expiry < 0)]
#     recommended = active_batches[0] if active_batches else None
    
#     return AvailableBatchesResponse(
#         ingredient_id=ingredient_id,
#         ingredient_name=ingredient.name,
#         unit=unit,
#         total_batches=len(batches),
#         total_available_quantity=Decimal(str(total_available)),
#         fresh_batches=fresh_count,
#         near_expiry_batches=near_expiry_count,
#         expired_batches=expired_count,
#         batches=batches,
#         recommended_batch=recommended,
#         warning=warning
#     )


# @router.post("/{dish_id}/ingredients/suggestion")
# def get_batch_suggestion(
#     dish_id: int,
#     ingredient_id: int,
#     quantity_required: float,
#     unit: str = "gm",
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user)
# ):
#     """
#     Get suggested batch for adding ingredient to dish
#     Call this before adding to show user the best batch to use
#     """
    
#     suggested_batch, message = DishIngredientService.get_batch_suggestion(
#         db=db,
#         tenant_id=current_user.tenant_id,
#         ingredient_id=ingredient_id,
#         quantity_required=quantity_required,
#         unit=unit
#     )
    
#     # Get ingredient name
#     ingredient = db.query(Inventory).filter(
#         Inventory.id == ingredient_id
#     ).first()
    
#     return {
#         "ingredient_id": ingredient_id,
#         "ingredient_name": ingredient.name if ingredient else "Unknown",
#         "quantity_required": quantity_required,
#         "unit": unit,
#         "suggested_batch": suggested_batch,
#         "message": message,
#         "can_add": suggested_batch is not None
#     }

# @router.post("/{dish_id}/ingredients/suggestion")
# def get_batch_suggestion(
#     dish_id: int,
#     ingredient_id: int,
#     quantity_required: float,
#     unit: str = "gm",
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user)
# ):
#     suggested_batch, message = DishIngredientService.get_batch_suggestion(
#         db=db,
#         tenant_id=current_user.tenant_id,
#         ingredient_id=ingredient_id,
#         quantity_required=quantity_required,
#         unit=unit
#     )
    
#     # Get ingredient name
#     ingredient = db.query(Inventory).filter(
#         Inventory.id == ingredient_id
#     ).first()
    
#     return {
#         "ingredient_id": ingredient_id,
#         "ingredient_name": ingredient.name if ingredient else "Unknown",
#         "quantity_required": quantity_required,
#         "unit": unit,
#         "suggested_batch": suggested_batch,
#         "message": message,
#         "can_add": suggested_batch is not None
#     }

# @router.post("/{dish_id}/ingredients/bulk")
# def add_multiple_ingredients_to_dish(
#     dish_id: int,
#     bulk_data: BulkDishIngredientAdd,
#     db: Session = Depends(get_db),
#     current_user:User = Depends(get_current_user)
# ):
#     """
#     Add multiple ingredients to a dish in one API call
    
#     Example request:
#     {
#       "ingredients": [
#         {
#           "ingredient_id": 1,
#           "quantity_required": 500,
#           "unit": "gm"
#         },
#         {
#           "ingredient_id": 2,
#           "quantity_required": 250,
#           "unit": "gm",
#           "preferred_batch_id": 42
#         },
#         {
#           "ingredient_id": 3,
#           "quantity_required": 100,
#           "unit": "ml"
#         }
#       ]
#     }
#     """
    
#     try:
#         result = DishIngredientService.add_multiple_ingredients_to_dish(
#             db=db,
#             tenant_id=current_user.tenant_id,
#             dish_id=dish_id,
#             ingredients_list=bulk_data.ingredients,
#             user_id=current_user.id
#         )
        
#         return {
#             "success": result["successful"] > 0,
#             "message": f"Added {result['successful']} of {result['total_requested']} ingredients",
#             **result
#         }
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.get("/dishes/{dish_id}/ingredients/batch-suggestions")
def get_batch_suggestions_for_ingredient(
    dish_id: int,
    ingredient_id: int,
    quantity_required: float,
    unit: str = "gm",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get FIFO/FEFO batch suggestions for ingredient
    Shows which batches to use in priority order
    Handles insufficient quantity
    Uses lifecycle from DB
    Provides allocation plan
    """
    
    # NEW: Function now returns a dict, not a list
    result = DishIngredientService.get_fifo_fefo_batch_suggestions(
        db=db,
        tenant_id=current_user.tenant_id,
        ingredient_id=ingredient_id,
        quantity_required=quantity_required,
        unit=unit
    )
    
    # Check if ingredient was found
    if not result.get("suggestions"):
        return {
            "success": False,
            "message": result["warnings"][0] if result.get("warnings") else "No available batches",
            **result
        }
    
    # Build response message
    if result["can_fulfill"]:
        if result["near_expiry_count"] > 0:
            message = f"Can fulfill {quantity_required}{unit}, but {result['near_expiry_count']} near-expiry batch(es) will be used"
        else:
            message = f"Can fulfill {quantity_required}{unit} from fresh batches"
    else:
        message = f"Insufficient quantity - shortage: {result['shortage']}{unit}"
    
    # Return complete result
    return {
        "success": result["can_fulfill"],
        "message": message,
        **result  # Includes all the new fields
    }

@router.post("/semi-finished/create")
def create_semi_finished_product(
    product_data: SemiFinishedProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create semi-finished product recipe (e.g., Dosa Batter, Masala Base)
    
    Example - Dosa Batter:
    {
      "name": "Dosa Batter",
      "product_type": "BATTER",
      "description": "Traditional South Indian dosa batter",
      "unit": "gm",
      "shelf_life_hours": 48,
      "storage_temp": "Refrigerated",
      "preparation_time_minutes": 480,
      "yield_quantity": 5000,
      "ingredients": [
        {"ingredient_id": 1, "quantity_required": 3000, "unit": "gm"},  // Rice
        {"ingredient_id": 2, "quantity_required": 1000, "unit": "gm"},  // Urad Dal
        {"ingredient_id": 3, "quantity_required": 10, "unit": "gm"}     // Fenugreek
      ]
    }
    """
    
    try:
        result = SemiFinishedService.create_semi_finished_product(
            db=db,
            tenant_id=current_user.tenant_id,
            product_data=product_data
        )
        
        return {
            "success": True,
            "message": f"Semi-finished product '{product_data.name}' created",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/semi-finished/produce")
def produce_semi_finished_batch(
    production: ProduceSemiFinished,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Produce a batch of semi-finished product
    
    Example - Make 5kg Dosa Batter:
    {
      "product_id": 1,
      "quantity_to_produce": 5000,
      "notes": "Morning batch for breakfast service"
    }
    
    This will:
    - Deduct raw ingredients (rice, urad dal, fenugreek) from inventory
    - Create stock batch of dosa batter
    - Calculate expiry based on shelf_life_hours
    """
    
    try:
        result = SemiFinishedService.produce_semi_finished_batch(
            db=db,
            tenant_id=current_user.tenant_id,
            product_id=production.product_id,
            quantity_to_produce=production.quantity_to_produce,
            user_id=current_user.id,
            notes=production.notes
        )
        
        return {
            "success": True,
            "message": f"Produced {production.quantity_to_produce} units of semi-finished product",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/semi-finished/{product_id}/stock")
def get_semi_finished_stock(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get available stock of semi-finished product
    Shows batches in FIFO/FEFO order
    """
    
    product = db.query(PrePreparedMaterial).filter(
        and_(
            PrePreparedMaterial.tenant_id == current_user.tenant_id,
            PrePreparedMaterial.id == product_id
        )
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stocks = SemiFinishedService.get_available_semi_finished_stock(
        db=db,
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        quantity_required=0  # Get all available
    )
    
    total_available = sum(s["quantity_remaining"] for s in stocks if s["status"] != "EXPIRED")
    near_expiry_count = sum(1 for s in stocks if s["is_near_expiry"])
    
    return {
        "product_id": product_id,
        "product_name": product.name,
        "total_available": total_available,
        "total_batches": len(stocks),
        "near_expiry_batches": near_expiry_count,
        "stocks": stocks,
        "warning": f"{near_expiry_count} batch(es) near expiry please use it " if near_expiry_count > 0 else None
    }

@router.post("/dishes/{dish_id}/ingredients")
def add_ingredient_to_dish(
    dish_id: int,
    ingredient: AddDishIngredient,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add ingredient to dish - supports both RAW and SEMI_FINISHED
    
    Example 1 - Add Raw Ingredient (Rice):
    {
      "ingredient_type": "RAW",
      "ingredient_id": 1,
      "quantity_required": 500,
      "unit": "gm"
    }
    
    Example 2 - Add Semi-Finished Product (Dosa Batter):
    {
      "ingredient_type": "SEMI_FINISHED",
      "semi_finished_product_id": 1,
      "quantity_required": 200,
      "unit": "gm"
    }
    """
    
    try:
        dish_ingredient, batch_or_stock, message = DishIngredientService.add_ingredient_to_dish(
            db=db,
            tenant_id=current_user.tenant_id,
            dish_id=dish_id,
            ingredient_data=ingredient
        )
        
        return {
            "success": True,
            "message": message,
            "ingredient_id": dish_ingredient.id,
            "ingredient_name": dish_ingredient.ingredient_name,
            "ingredient_type": ingredient.ingredient_type,
            "quantity_required": dish_ingredient.quantity_required,
            "assigned": batch_or_stock
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dishes/{dish_id}/ingredients/bulk")
def add_multiple_ingredients(
    dish_id: int,
    data: BulkDishIngredientAdd,
    db: Session = Depends(get_db),
    current_user:User = Depends(get_current_user)
):
    """
    Add multiple ingredients to dish at once
    Each ingredient gets automatic FIFO/FEFO batch assignment
    """
    
    result = DishIngredientService.add_multiple_ingredients(
        db=db,
        tenant_id=current_user.tenant_id,
        dish_id=dish_id,
        ingredients_list=data.ingredients
    )

    return{
        "result":result
    }

@router.post("/prepare", response_model=dict)
def prepare_single_dish(
    request: SingleDishPreparation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Prepare a single dish and automatically deduct inventory
    
    **Example Request:**
```json
    {
      "dish_id": 5,
      "quantity": 3,
      "notes": "Table 7 customer order"
    }
```
    
    **Response:**
    - Preparation log ID
    - Dish details
    - Ingredients consumed with batch numbers
    - Total cost breakdown
    - Inventory deduction status
    """
    try:
        result = DishPreparationService.prepare_dish(
            db=db,
            tenant_id=current_user.tenant_id,
            dish_id=request.dish_id,
            quantity=request.quantity,
            user_id=current_user.id,
            notes=request.notes,
            batch_id=None  # Single dish, no batch
        )
        
        return {
            "success": True,
            "message": f"Successfully prepared {request.quantity} x {result.dish_name}",
            "data": {
                "preparation_log_id": result.preparation_log_id,
                "dish_id": result.dish_id,
                "dish_name": result.dish_name,
                "quantity_prepared": result.quantity_prepared,
                "total_cost": result.total_cost,
                "cost_per_unit": round(result.total_cost / result.quantity_prepared, 2) if result.quantity_prepared > 0 else 0,
                "inventory_deducted": result.inventory_deducted,
                "preparation_date": result.preparation_date,
                "user": {
                    "id": current_user.id,
                    "name": current_user.full_name
                },
                "ingredients_consumed": result.ingredients_consumed
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare dish: {str(e)}"
        )

@router.patch("/log/{log_id}/status")
def update_preparation_status(
    log_id: int,
    status: PreparationBatchStatus,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually update the status of a dish preparation
    Ensures atomic transaction (all-or-nothing)
    """

    try:
        prep_log = db.query(DishPreparationBatchLog).filter(
            DishPreparationBatchLog.tenant_id == current_user.tenant_id,
            DishPreparationBatchLog.id == log_id
        ).first()

        if not prep_log:
            raise HTTPException(status_code=404, detail="Preparation log not found")

        old_status = prep_log.track_status

        # Update status
        prep_log.track_status = status

        if notes:
            prep_log.notes = f"{prep_log.notes or ''}\nStatus update: {notes}".strip()

        # Set completed_at for final states
        if status in {
            PreparationBatchStatus.COMPLETED,
            PreparationBatchStatus.CANCELLED
        }:
            if not prep_log.completed_at:
                prep_log.completed_at = datetime.utcnow()

        # Force validation before commit
        db.flush()

        # Commit only if everything is OK
        db.commit()
        db.refresh(prep_log)

        return {
            "success": True,
            "message": f"Status updated from {old_status.value} to {status.value}",
            "log_id": prep_log.id,
            "old_status": old_status.value,
            "new_status": prep_log.track_status.value,
            "completed_at": prep_log.completed_at
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update preparation status"
        )

# api for prepare multiple dishes
@router.post("/batch-prepare", response_model=dict)
def prepare_batch_of_dishes(
    request: BatchDishPreparation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Prepare multiple dishes simultaneously in one batch
    
    **Use Cases:**
    - Morning prep for breakfast service
    - Catering orders
    - Bulk cooking sessions
    
    **Example Request:**
```json
    {
      "batch_notes": "Morning breakfast service",
      "preparations": [
        {
          "dish_id": 5,
          "quantity": 10,
          "notes": "Masala Dosa - Regular spice"
        },
        {
          "dish_id": 7,
          "quantity": 8,
          "notes": "Idli - Soft"
        },
        {
          "dish_id": 9,
          "quantity": 6,
          "notes": "Vada - Crispy"
        }
      ]
    }
```
    
    **Response:**
    - Batch ID and number
    - Status (COMPLETED, PARTIALLY_COMPLETED, etc.)
    - Success/failure counts
    - Total cost and duration
    - Individual preparation results
    - Warnings (if any)
    """
    try:
        result = DishPreparationService.prepare_multiple_dishes_batch(
            db=db,
            tenant_id=current_user.tenant_id,
            preparations=request.preparations,
            user_id=current_user.id,
            batch_notes=request.batch_notes
        )
        
        return {
            "success": result.successful > 0,
            "message": (
                f"Batch preparation {result.status}. "
                f"{result.successful} successful, {result.failed} failed"
            ),
            "data": {
                "batch_id": result.batch_id,
                "batch_number": result.batch_number,
                "status": result.status,
                "summary": {
                    "total_dishes_prepared": result.total_dishes_prepared,
                    "successful_preparations": result.successful,
                    "failed_preparations": result.failed,
                    "total_cost": result.total_cost,
                    "average_cost_per_dish": round(
                        result.total_cost / result.total_dishes_prepared, 2
                    ) if result.total_dishes_prepared > 0 else 0
                },
                "timing": {
                    "started_at": result.started_at,
                    "completed_at": result.completed_at,
                    "duration_minutes": result.duration_minutes
                },
                "chef": {
                    "id": current_user.id,
                    "name": current_user.full_name
                },
                "preparations": [
                    {
                        "preparation_log_id": prep.preparation_log_id,
                        "dish_id": prep.dish_id,
                        "dish_name": prep.dish_name,
                        "quantity_prepared": prep.quantity_prepared,
                        "total_cost": prep.total_cost,
                        "cost_per_unit": round(
                            prep.total_cost / prep.quantity_prepared, 2
                        ) if prep.quantity_prepared > 0 else 0,
                        "ingredients_consumed": prep.ingredients_consumed
                    }
                    for prep in result.preparations
                ],
                "warnings": result.warnings
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare batch: {str(e)}"
        )

@router.get("/history", response_model=dict)
def get_preparation_history(
    dish_id: Optional[int] = Query(None, description="Filter by dish ID"),
    user_id: Optional[int] = Query(None, description="Filter by chef/user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get preparation history with optional filters
    
    **Query Parameters:**
    - `dish_id`: Filter by specific dish
    - `user_id`: Filter by specific chef
    - `start_date`: From date (e.g., 2026-01-20T00:00:00)
    - `end_date`: To date (e.g., 2026-01-24T23:59:59)
    - `limit`: Max records (default: 100, max: 500)
    - `offset`: Skip records (for pagination)
    
    **Examples:**
```
    # Get last 50 preparations for dish ID 5
    GET /dish-preparation/history?dish_id=5&limit=50
    
    # Get today's preparations
    GET /dish-preparation/history?start_date=2026-01-24T00:00:00&end_date=2026-01-24T23:59:59
    
    # Get preparations by chef Ramesh
    GET /dish-preparation/history?user_id=42
    
    # Pagination (page 2, 20 per page)
    GET /dish-preparation/history?limit=20&offset=20
```
    """
    try:
        history = DishPreparationService.get_preparation_history(
            db=db,
            tenant_id=current_user.tenant_id,
            dish_id=dish_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Calculate summary statistics
        total_preparations = len(history)
        total_dishes = sum(h["quantity_prepared"] for h in history)
        total_cost = sum(h["total_cost"] for h in history)
        
        # Apply offset for pagination
        paginated_history = history[offset:offset + limit] if offset < len(history) else []
        
        return {
            "success": True,
            "filters": {
                "dish_id": dish_id,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            },
            "pagination": {
                "total": total_preparations,
                "limit": limit,
                "offset": offset,
                "returned": len(paginated_history),
                "has_more": (offset + len(paginated_history)) < total_preparations
            },
            "summary": {
                "total_preparations": total_preparations,
                "total_dishes_prepared": total_dishes,
                "total_cost": round(total_cost, 2),
                "average_cost_per_preparation": round(
                    total_cost / total_preparations, 2
                ) if total_preparations > 0 else 0,
                "average_dishes_per_preparation": round(
                    total_dishes / total_preparations, 2
                ) if total_preparations > 0 else 0
            },
            "data": paginated_history
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch preparation history: {str(e)}"
        )

@router.get("/preparations/{preparation_id}", response_model=dict)
def get_preparation_details(
    preparation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific preparation
    
    **Returns:**
    - Complete preparation details
    - Dish information
    - Chef information
    - Ingredient consumption breakdown with batch numbers
    - Cost analysis
    - Batch information (if part of batch)
    
    **Example:**
```
    GET /dish-preparation/preparations/101
```
    """
    try:
        
        # Get preparation log
        prep_log = db.query(DishPreparationBatchLog).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                DishPreparationBatchLog.id == preparation_id
            )
        ).first()
        
        if not prep_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preparation with ID {preparation_id} not found"
            )
        
        # Get related data
        dish = db.query(Dish).filter(Dish.id == prep_log.dish_id).first()
        user = db.query(User).filter(User.id == prep_log.user_id).first()
        consumptions = db.query(PreparationIngredientHistory).filter(
            PreparationIngredientHistory.preparation_log_id == prep_log.id
        ).all()
        
        # Get batch info if applicable
        batch_info = None
        if prep_log.batch_id:
            batch = db.query(DishPreparationBatch).filter(
                DishPreparationBatch.id == prep_log.batch_id
            ).first()
            if batch:
                batch_info = {
                    "batch_id": batch.id,
                    "batch_number": batch.batch_number,
                    "status": batch.status.value if hasattr(batch.status, 'value') else str(batch.status)
                }
        
        return {
            "success": True,
            "data": {
                "preparation_id": prep_log.id,
                "dish": {
                    "id": dish.id if dish else None,
                    "name": dish.name if dish else "Unknown",
                    # "category": dish.type_id.name if dish else None
                },
                "chef": {
                    "id": user.id if user else None,
                    "name": user.full_name if user else "Unknown",
                    "email": user.email if user else None
                },
                "batch": batch_info,
                "quantity_prepared": prep_log.quantity_prepared,
                "preparation_date": prep_log.preparation_date,
                "notes": prep_log.notes,
                "costs": {
                    "total_cost": float(prep_log.total_cost),
                    "cost_per_unit": round(
                        float(prep_log.total_cost) / prep_log.quantity_prepared, 2
                    ) if prep_log.quantity_prepared > 0 else 0
                },
                "inventory_deducted": prep_log.inventory_deducted,
                "ingredients_consumed": [
                    {
                        "ingredient_name": c.ingredient_name,
                        "batch_number": c.batch_number,
                        "quantity_consumed": float(c.quantity_consumed),
                        "unit": c.unit,
                        "cost_per_unit": float(c.cost_per_unit),
                        "total_cost": float(c.total_cost)
                    }
                    for c in consumptions
                ],
                "created_at": prep_log.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch preparation details: {str(e)}"
        )

#api for how many dish prepared in the day
@router.get("/today-report", response_model=dict)
def get_today_production_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive production report for today
    
    **Includes:**
    - Total dishes prepared
    - Cost breakdown by dish
    - Chef performance
    - Peak hours analysis
    - Most popular dishes
    
    **Example:**
```
    GET /dish-preparation/today-report
```
    """
    try:
        today = date.today()
        
        # Get all today's preparations
        preparations = db.query(DishPreparationBatchLog).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                func.date(DishPreparationBatchLog.preparation_date) == today
            )
        ).all()
        
        # Summary statistics
        total_preparations = len(preparations)
        total_dishes = sum(p.quantity_prepared for p in preparations)
        total_cost = sum(float(p.total_cost) for p in preparations)
        
        # By dish breakdown
        dish_stats = db.query(
            Dish.id,
            Dish.name,
            # Dish.category,
            func.sum(DishPreparationBatchLog.quantity_prepared).label('total_prepared'),
            func.sum(DishPreparationBatchLog.total_cost).label('total_cost'),
            func.count(DishPreparationBatchLog.id).label('preparations_count')
        ).join(
            DishPreparationBatchLog, Dish.id == DishPreparationBatchLog.dish_id
        ).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                func.date(DishPreparationBatchLog.preparation_date) == today
            )
        ).group_by(Dish.id, Dish.name).order_by(
            func.sum(DishPreparationBatchLog.quantity_prepared).desc()
        ).all()
        
        # By chef breakdown
        chef_stats = db.query(
            User.id,
            User.full_name,
            func.count(DishPreparationBatchLog.id).label('preparations_count'),
            func.sum(DishPreparationBatchLog.quantity_prepared).label('total_dishes'),
            func.sum(DishPreparationBatchLog.total_cost).label('total_cost')
        ).join(
            DishPreparationBatchLog, User.id == DishPreparationBatchLog.user_id
        ).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                func.date(DishPreparationBatchLog.preparation_date) == today
            )
        ).group_by(User.id, User.full_name).order_by(
            func.sum(DishPreparationBatchLog.quantity_prepared).desc()
        ).all()
        
        # Peak hours
        peak_hours = db.query(
            extract('hour', DishPreparationBatchLog.preparation_date).label('hour'),
            func.count(DishPreparationBatchLog.id).label('preparations'),
            func.sum(DishPreparationBatchLog.quantity_prepared).label('dishes')
        ).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                func.date(DishPreparationBatchLog.preparation_date) == today
            )
        ).group_by('hour').order_by(
            func.sum(DishPreparationBatchLog.quantity_prepared).desc()
        ).limit(5).all()
        
        return {
            "success": True,
            "date": today,
            "summary": {
                "total_preparations": total_preparations,
                "total_dishes_prepared": total_dishes,
                "total_cost": round(total_cost, 2),
                "average_cost_per_dish": round(
                    total_cost / total_dishes, 2
                ) if total_dishes > 0 else 0,
                "average_dishes_per_preparation": round(
                    total_dishes / total_preparations, 2
                ) if total_preparations > 0 else 0
            },
            "by_dish": [
                {
                    "dish_id": stat.id,
                    "dish_name": stat.name,
                    # "category": stat.category,
                    "total_prepared": stat.total_prepared,
                    "total_cost": round(float(stat.total_cost), 2),
                    "average_cost": round(
                        float(stat.total_cost) / stat.total_prepared, 2
                    ) if stat.total_prepared > 0 else 0,
                    "preparations_count": stat.preparations_count
                }
                for stat in dish_stats
            ],
            "by_chef": [
                {
                    "user_id": stat.id,
                    "chef_name": stat.full_name,
                    "preparations_count": stat.preparations_count,
                    "total_dishes": stat.total_dishes,
                    "total_cost": round(float(stat.total_cost), 2),
                    "average_cost_per_dish": round(
                        float(stat.total_cost) / stat.total_dishes, 2
                    ) if stat.total_dishes > 0 else 0
                }
                for stat in chef_stats
            ],
            "peak_hours": [
                {
                    "hour": int(stat.hour),
                    "hour_formatted": f"{int(stat.hour):02d}:00",
                    "preparations": stat.preparations,
                    "dishes": stat.dishes
                }
                for stat in peak_hours
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )

#batch details
@router.get("/batches/{batch_id}", response_model=dict)
def get_batch_details(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a preparation batch
    
    **Returns:**
    - Batch information
    - All dishes prepared in batch
    - Cost breakdown
    - Duration and status
    - Chef information
    
    **Example:**
```
    GET /dish-preparation/batches/15
```
    """
    try:
        # Get batch
        batch = db.query(DishPreparationBatch).filter(
            and_(
                DishPreparationBatch.tenant_id == current_user.tenant_id,
                DishPreparationBatch.id == batch_id
            )
        ).first()
        
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch with ID {batch_id} not found"
            )
        
        # Get all preparations in batch
        preparations = db.query(DishPreparationBatchLog).filter(
            DishPreparationBatchLog.batch_id == batch_id
        ).all()
        
        # Build dish list
        dishes = []
        for prep in preparations:
            dish = db.query(Dish).filter(Dish.id == prep.dish_id).first()
            dishes.append({
                "preparation_id": prep.id,
                "dish_id": prep.dish_id,
                "dish_name": dish.name if dish else "Unknown",
                "quantity_prepared": prep.quantity_prepared,
                "total_cost": float(prep.total_cost),
                "cost_per_unit": round(
                    float(prep.total_cost) / prep.quantity_prepared, 2
                ) if prep.quantity_prepared > 0 else 0,
                "notes": prep.notes
            })
        
        # Calculate duration
        duration = None
        if batch.completed_at and batch.started_at:
            delta = batch.completed_at - batch.started_at
            duration = int(delta.total_seconds() / 60)
        
        return {
            "success": True,
            "data": {
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "status": batch.status.value if hasattr(batch.status, 'value') else str(batch.status),
                "chef": {
                    "id": batch.user_id,
                    "name": batch.user.full_name if batch.user else "Unknown"
                },
                "summary": {
                    "total_dishes_planned": batch.total_dishes_planned,
                    "total_dishes_completed": batch.total_dishes_completed,
                    "completion_rate": round(
                        (batch.total_dishes_completed / batch.total_dishes_planned * 100), 2
                    ) if batch.total_dishes_planned > 0 else 0,
                    "total_cost": float(batch.total_cost),
                    "average_cost_per_dish": round(
                        float(batch.total_cost) / batch.total_dishes_completed, 2
                    ) if batch.total_dishes_completed > 0 else 0
                },
                "timing": {
                    "started_at": batch.started_at,
                    "completed_at": batch.completed_at,
                    "duration_minutes": duration
                },
                "notes": batch.notes,
                "dishes": dishes
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch details: {str(e)}"
        )

#analytics api
@router.get("/statistics/dish/{dish_id}", response_model=dict)
def get_dish_preparation_statistics(
    dish_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get preparation statistics for a specific dish
    
    **Includes:**
    - Total prepared in period
    - Average cost per unit
    - Preparation frequency
    - Cost trends (min/max/average)
    
    **Example:**
```
    # Get last 30 days statistics for dish ID 5
    GET /dish-preparation/statistics/dish/5?days=30
    
    # Get last 90 days
    GET /dish-preparation/statistics/dish/5?days=90
```
    """
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # Get dish
        dish = db.query(Dish).filter(
            and_(
                Dish.tenant_id == current_user.tenant_id,
                Dish.id == dish_id
            )
        ).first()
        
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dish with ID {dish_id} not found"
            )
        
        # Get statistics
        stats = db.query(
            func.count(DishPreparationBatchLog.id).label('total_preparations'),
            func.sum(DishPreparationBatchLog.quantity_prepared).label('total_quantity'),
            func.sum(DishPreparationBatchLog.total_cost).label('total_cost'),
            func.avg(DishPreparationBatchLog.total_cost / DishPreparationBatchLog.quantity_prepared).label('avg_cost_per_unit'),
            func.min(DishPreparationBatchLog.total_cost / DishPreparationBatchLog.quantity_prepared).label('min_cost_per_unit'),
            func.max(DishPreparationBatchLog.total_cost / DishPreparationBatchLog.quantity_prepared).label('max_cost_per_unit')
        ).filter(
            and_(
                DishPreparationBatchLog.tenant_id == current_user.tenant_id,
                DishPreparationBatchLog.dish_id == dish_id,
                DishPreparationBatchLog.preparation_date >= start_date
            )
        ).first()
        
        return {
            "success": True,
            "dish": {
                "id": dish.id,
                "name": dish.name,
                # "category": dish.category
            },
            "period": {
                "days": days,
                "start_date": start_date,
                "end_date": datetime.now()
            },
            "statistics": {
                "total_preparations": stats.total_preparations or 0,
                "total_quantity_prepared": stats.total_quantity or 0,
                "total_cost": round(float(stats.total_cost), 2) if stats.total_cost else 0,
                "average_cost_per_unit": round(float(stats.avg_cost_per_unit), 2) if stats.avg_cost_per_unit else 0,
                "min_cost_per_unit": round(float(stats.min_cost_per_unit), 2) if stats.min_cost_per_unit else 0,
                "max_cost_per_unit": round(float(stats.max_cost_per_unit), 2) if stats.max_cost_per_unit else 0,
                "average_quantity_per_preparation": round(
                    float(stats.total_quantity / stats.total_preparations), 2
                ) if stats.total_preparations else 0,
                "preparation_frequency_per_day": round(
                    float(stats.total_preparations / days), 2
                ) if days > 0 else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )


# @router.post("/add_dish")
# def add_dish(request: AddDishRequest, db: Session = Depends(get_db)):
#     # Check if dish with same name exists
#     existing_dish = db.query(Dish).filter(Dish.name == request.name).first()
#     if existing_dish:
#         raise HTTPException(status_code=400, detail="Dish with this name already exists.")

#     # Get or create DishType
#     dish_type = db.query(DishType).filter(DishType.name == request.type).first()
#     if not dish_type:
#         dish_type = DishType(name=request.type)
#         db.add(dish_type)
#         db.commit()
#         db.refresh(dish_type)

#     # Create new dish
#     new_dish = Dish(name=request.name, type_id=dish_type.id)
#     db.add(new_dish)
#     db.commit()
#     db.refresh(new_dish)

#     # Process ingredients
#     for ing in request.ingredients:
#         unit = getattr(ing, "unit", "gm")
#         cost_per_unit = getattr(ing, "cost_per_unit", 0.0)
#         dish_ingredient = DishIngredient(
#             dish_id=new_dish.id,
#             ingredient_name=ing.name,
#             quantity_required=ing.quantity_required,
#             unit=unit,
#             cost_per_unit=cost_per_unit
#         )
#         db.add(dish_ingredient)

#     db.commit()
#     return {"message": f"Dish '{request.name}' added successfully with ingredients."}


@router.get("/dishes", response_model=List[DishOut])
def list_dishes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
                ):
    

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )

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
def search_dishes_by_name(
    partial_name: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required",
            )
    
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
            tenant_id=dish.tenant_id,
            type_id=dish.type_id,
            type=DishTypeOut(
                id=dish.type.id,
                name=dish.type.name
            ),
            ingredients=ingredient_list
        ))

    return result


# @router.delete("/dishes/{dish_name}")
# def delete_dish_by_name(
#     dish_name: str,
#     confirm: bool = Query(False, description="Set to true to confirm deletion"),
#     db: Session = Depends(get_db)
# ):
#     dish = db.query(Dish).filter(Dish.name.ilike(dish_name)).first()
#     if not dish:
#         raise HTTPException(status_code=404, detail="Dish not found")

#     if not confirm:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Deletion not confirmed. To delete dish '{dish.name}', set confirm=true."
#         )

#     db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).delete()
#     db.delete(dish)
#     db.commit()
#     return {"message": f"Dish '{dish.name}' deleted successfully"}

# @router.get("/dish_types")
# def get_dish_types(db: Session = Depends(get_db)):
#     dish_types = db.query(DishType).all()
#     return [dt.name for dt in dish_types]

# @router.get("/dishes/{dish_id}/cost")
# def get_dish_cost(dish_id: int, db: Session = Depends(get_db)):
#     dish = db.query(Dish).filter(Dish.id == dish_id).first()
#     if not dish:
#         raise HTTPException(status_code=404, detail="Dish not found")

#     ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()
#     total_cost = 0.0
#     ingredient_costs = []

#     for di in ingredients:
#         # Get the most recent inventory item for this ingredient
#         inventory_item = db.query(Inventory).filter(
#             Inventory.name.ilike(di.ingredient_name)
#         ).order_by(Inventory.date_added.desc()).first()

#         print(di.ingredient_name,"INGREDINETS")

#         if not inventory_item:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Ingredient '{di.ingredient_name}' not found in inventory"
#             )
#         print(di.ingredient_name,"INGREDIENT NAME")

#         item_cost = di.quantity_required * inventory_item.price_per_unit
#         total_cost += item_cost

#         ingredient_costs.append({
#             "ingredient": di.ingredient_name,
#             "quantity_required": di.quantity_required,
#             "unit_price": inventory_item.price_per_unit,
#             "total_cost": item_cost
#         })

#     return {
#         "dish_id": dish.id,
#         "dish_name": dish.name,
#         "ingredient_breakdown": ingredient_costs,
#         "total_cost": round(total_cost, 2)
#     }


# @router.put("/dishes/{dish_id}")
# def update_dish(dish_id: int, payload: DishUpdate, db: Session = Depends(get_db)):
#     dish = db.query(Dish).filter(Dish.id == dish_id).first()
#     if not dish:
#         raise HTTPException(status_code=404, detail="Dish not found")

#     # Update dish name and type
#     dish.name = payload.name

#     # Lookup or create dish type
#     dish_type = db.query(DishType).filter(DishType.name.ilike(payload.type)).first()
#     if not dish_type:
#         dish_type = DishType(name=payload.type)
#         db.add(dish_type)
#         db.commit()
#         db.refresh(dish_type)
#     dish.type_id = dish_type.id
#     db.commit()

#     # Fetch existing ingredients
#     dish_ingredients = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()
#     existing_ingredients = {di.ingredient_name.lower(): di for di in dish_ingredients}
#     updated_names = {ing.ingredient_name.lower() for ing in payload.ingredients}

#     for ing in payload.ingredients:
#         key = ing.ingredient_name.lower()
#         unit = getattr(ing, "unit", "gm")
#         cost_per_unit = getattr(ing, "cost_per_unit", 0.0)
#         if key in existing_ingredients:
#             existing_ingredients[key].quantity_required = ing.quantity_required
#             existing_ingredients[key].unit = unit
#             existing_ingredients[key].cost_per_unit = cost_per_unit
#         else:
#             db.add(DishIngredient(
#                 dish_id=dish.id,
#                 ingredient_name=ing.ingredient_name,
#                 quantity_required=ing.quantity_required,
#                 unit=unit,
#                 cost_per_unit=cost_per_unit
#             ))

#     # Delete ingredients no longer in request
#     for key, di in existing_ingredients.items():
#         if key not in updated_names:
#             db.delete(di)

#     db.commit()
#     return {"message": "Dish updated successfully"}