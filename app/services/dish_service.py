from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime , timedelta, timezone
from typing import Dict, List,Optional,Tuple
from decimal import Decimal
from app.models.dish import Dish, DishIngredient, DishPreparationBatch , PrePreparedMaterial, PreparationBatchStatus,PreparationIngredientHistory,PrePreparedMaterialStock,IngredientForPrePreparedIngredients,DishPreparationBatchLog
from app.models.inventory import Inventory,InventoryBatch, InventoryTransaction, PerishableLifecycle, TransactionType
from app.models.users import User
from app.schemas.dish import BatchInfo, BatchPreparationResult,DishCreate,DishIngredientResponse, DishIngredientType,DishTypeUpdate,DishUpdate,AddDishIngredient,PreparationResult,SemiFinishedProductCreate, SingleDishPreparation
from uuid import UUID
import uuid
from enum import Enum
from app.utils.common_unit_converter import convert_quantity_unit

class SemiFinishedService:

    @staticmethod
    def create_semi_finished_product(
        db: Session,
        tenant_id: int,
        product_data: SemiFinishedProductCreate
    ) -> dict:
        """
        Create semi-finished product recipe (e.g., Dosa Batter)
        Define raw ingredients needed to make it
        """
        
        # Create product
        product = PrePreparedMaterial(
            tenant_id=tenant_id,
            name=product_data.name,
            product_type=product_data.product_type,
            description=product_data.description,
            unit=product_data.unit,
            shelf_life_hours=product_data.shelf_life_hours,
            preparation_time_minutes=product_data.preparation_time_minutes,
            yield_quantity=Decimal(str(product_data.yield_quantity)),
            storage_location_id=product_data.storage_location_id
        )
        db.add(product)
        db.flush()
        
        total_cost = Decimal(0)
        
        # Add raw ingredients using FIFO/FEFO
        for ing_data in product_data.ingredients:

            ingredient = db.query(Inventory).filter(
                    and_(
                        Inventory.tenant_id == tenant_id,
                        Inventory.id == ing_data.ingredient_id
                    )
                ).first()
            

            if not ingredient:
                raise ValueError(f"Ingredient {ing_data.ingredient_id} not found")

            qty_in_inventory_unit = convert_quantity_unit(
                value=Decimal(str(ing_data.quantity_required)),
                from_unit=ing_data.unit,
                to_unit=ingredient.unit
            )
            batches = db.query(InventoryBatch).filter(
                and_(
                    InventoryBatch.tenant_id == tenant_id,
                    InventoryBatch.inventory_item_id == ing_data.ingredient_id,
                    InventoryBatch.is_active == True,
                    InventoryBatch.quantity_remaining > 0
                )
            ).all()

            if batches:
                batch_suggestions_result = DishIngredientService.get_fifo_fefo_batch_suggestions(
                        db=db,
                        tenant_id=tenant_id,
                        ingredient_id=ing_data.ingredient_id,
                        quantity_required=ing_data.quantity_required,
                        unit=ing_data.unit
                    )
                if not batch_suggestions_result.get("can_fulfill", False):
                    raise ValueError(
                        f"Cannot fulfill requirement for {ingredient.name}: "
                        f"{', '.join(batch_suggestions_result.get('warnings', []))}"
                    )
                
                suggestions = batch_suggestions_result.get("suggestions", [])
                active = [s for s in suggestions if s.lifecycle_stage != "EXPIRED"]

                if not active:
                    raise ValueError(f"All batches expired for {ingredient.name}")
                
                selected = active[0] if not ing_data.preferred_batch_id else next(
                    (s for s in active if s.batch_id == ing_data.preferred_batch_id),
                    active[0]
                )

                batch = db.query(InventoryBatch).filter(
                        InventoryBatch.id == selected.batch_id
                    ).first()
                
                # Create transaction
                transaction = InventoryTransaction(
                    tenant_id=tenant_id,
                    inventory_item_id=ing_data.ingredient_id,
                    batch_id=batch.id,
                    transaction_type=TransactionType.PREPARATION,
                    quantity=Decimal(str(ing_data.quantity_required)),
                    unit_cost=batch.unit_cost,
                    total_value=Decimal(str(ing_data.quantity_required)) * (batch.unit_cost or Decimal(0)),
                    pre_prepared_material_id=product.id
                )
                db.add(transaction)
                db.flush()

                unit_cost = batch.unit_cost or Decimal(0)

            else:  

                current_qty = Decimal(str(ingredient.current_quantity)) if ingredient.current_quantity else Decimal(0)
                if current_qty < qty_in_inventory_unit:
                        raise ValueError(
                            f"Insufficient {ingredient.name}. "
                            f"Available: {float(current_qty)} {ingredient.unit}, "
                            f"Required: {float(qty_in_inventory_unit)} {ingredient.unit}"
                        )
                
                if ingredient.expiry_date:
                    today = datetime.now(timezone.utc).date()
                    if ingredient.expiry_date < today:
                        days_expired = (today - ingredient.expiry_date).days
                        raise ValueError(
                            f"Cannot use {ingredient.name} - EXPIRED {days_expired} day{'s' if days_expired != 1 else ''} ago "
                            f"(expired on {ingredient.expiry_date})"
                        )
                    
                ingredient.current_quantity = float(current_qty - qty_in_inventory_unit)

                transaction = InventoryTransaction(
                    tenant_id=tenant_id,
                    inventory_item_id=ing_data.ingredient_id,
                    batch_id=None,                                                          # no batch
                    transaction_type=TransactionType.PREPARATION,
                    quantity=Decimal(str(ing_data.quantity_required)),                       # recipe unit
                    unit_cost=ingredient.unit_cost or Decimal(0),                           # cost from inventory
                    total_value=qty_in_inventory_unit * (ingredient.unit_cost or Decimal(0)),
                    pre_prepared_material_id=product.id
                )
                db.add(transaction)
                db.flush()

                unit_cost = ingredient.unit_cost or Decimal(0)
                
                # Add to semi-finished ingredients
            sf_ingredient = IngredientForPrePreparedIngredients(
                    tenant_id=tenant_id,
                    semi_finished_product_id=product.id,
                    ingredient_id=ing_data.ingredient_id,
                    inventory_transaction_id=transaction.id,
                    quantity_required=Decimal(str(ing_data.quantity_required)),
                    ingredient_name=ingredient.name if ingredient else "Unknown",
                    unit=ing_data.unit,
                    cost_per_unit=unit_cost
                )
            db.add(sf_ingredient)
                
            total_cost += qty_in_inventory_unit * unit_cost
            
            # Calculate cost per unit
        if product_data.yield_quantity > 0:
                product.cost_per_unit = total_cost / Decimal(str(product_data.yield_quantity))
            
        db.commit()
        db.refresh(product)
            
        return {
                "product_id": product.id,
                "name": product.name,
                "yield_quantity": float(product.yield_quantity),
                "cost_per_unit": float(product.cost_per_unit),
                "total_cost": float(total_cost)
            }
    
    @staticmethod
    def produce_semi_finished_batch(
        db: Session,
        tenant_id: int,
        product_id: UUID,
        quantity_to_produce: float,
        user_id: int,
        notes: Optional[str] = None
    ) -> dict:
        """
        Produce a batch of semi-finished product
        Deducts raw ingredients from inventory
        Creates stock batch for later use
        """
        
        # Get product
        product = db.query(PrePreparedMaterial).filter(
            and_(PrePreparedMaterial.tenant_id == tenant_id, PrePreparedMaterial.id == product_id)
        ).first()
        
        if not product:
            raise ValueError("Semi-finished product not found")
        
        # Get ingredients
        ingredients = db.query(IngredientForPrePreparedIngredients).filter(
            IngredientForPrePreparedIngredients.semi_finished_product_id == product_id
        ).all()
        
        if not ingredients:
            raise ValueError("No ingredients configured for this product")
        
        # Calculate multiplier (how many times to scale recipe)
        multiplier = Decimal(str(quantity_to_produce)) / product.yield_quantity
        
        total_cost = Decimal(0)
        consumptions = []
        
        # Deduct raw ingredients
        for ing in ingredients:
            qty_needed = ing.quantity_required * multiplier

            # Get inventory first (needed for unit and standalone fallback)
            inventory = db.query(Inventory).filter(
                and_(
                    Inventory.tenant_id == tenant_id,
                    Inventory.id == ing.ingredient_id
                )
            ).first()

            if not inventory:
                raise ValueError(f"Inventory not found for {ing.ingredient_name}")

            # Convert recipe qty to inventory unit
            qty_in_inventory_unit = convert_quantity_unit(
                value=qty_needed,
                from_unit=ing.unit,
                to_unit=inventory.unit
            )

            # Check if batches exist
            batches = db.query(InventoryBatch).filter(
                and_(
                    InventoryBatch.tenant_id == tenant_id,
                    InventoryBatch.inventory_item_id == ing.ingredient_id,
                    InventoryBatch.is_active == True,
                    InventoryBatch.quantity_remaining > 0
                )
            ).order_by(
                InventoryBatch.expiry_date.asc().nullslast(),
                InventoryBatch.created_at.asc()
            ).all()

            if batches: # use batches as fifo/fefo

                # Check total available across ALL batches
                total_available = sum(
                    Decimal(str(b.quantity_remaining)) for b in batches
                )

                if total_available < qty_in_inventory_unit:
                    raise ValueError(
                        f"Insufficient {ing.ingredient_name}. "
                        f"Available: {float(total_available)} {inventory.unit}, "
                        f"Required: {float(qty_in_inventory_unit)} {inventory.unit}"
                    )
                
                # Allocate across multiple batches (FIFO/FEFO)
                qty_remaining = qty_in_inventory_unit
                ingredient_cost = Decimal(0)

                for batch in batches:
                    if qty_remaining <= 0:
                        break

                    batch_qty_remaining = Decimal(str(batch.quantity_remaining))
                    batch_unit_cost = Decimal(str(batch.unit_cost)) if batch.unit_cost else Decimal(0)

                    # Take as much as needed or available in this batch
                    qty_from_batch = min(batch_qty_remaining, qty_remaining)

                    # DEDUCT from batch
                    batch.quantity_remaining = float(batch_qty_remaining - qty_from_batch)

                    # Calculate cost for this batch
                    cost = qty_from_batch * batch_unit_cost
                    ingredient_cost += cost

                    # Log each batch used in consumptions
                    consumptions.append({
                        "ingredient_name": ing.ingredient_name,
                        "batch_number": batch.batch_number,
                        "quantity_consumed": float(qty_from_batch),
                        "unit": inventory.unit,
                        "quantity_consumed_recipe_unit": float(
                            convert_quantity_unit(
                                value=qty_from_batch,
                                from_unit=inventory.unit,
                                to_unit=ing.unit
                            )
                        ),
                        "recipe_unit": ing.unit,
                        "cost": float(cost)
                    })

                    qty_remaining -= qty_from_batch

                # DEDUCT from inventory total (once per ingredient, outside batch loop)
                current_qty = Decimal(str(inventory.current_quantity)) if inventory.current_quantity else Decimal(0)
                inventory.current_quantity = float(current_qty - qty_in_inventory_unit)

                total_cost += ingredient_cost

            else: # use inventory items directly
                current_qty = Decimal(str(inventory.current_quantity)) if inventory.current_quantity else Decimal(0)

                if current_qty < qty_in_inventory_unit:
                    raise ValueError(
                        f"Insufficient {ing.ingredient_name}. "
                        f"Available: {float(current_qty)} {inventory.unit}, "
                        f"Required: {float(qty_in_inventory_unit)} {inventory.unit}"
                    )
                
                if inventory.expiry_date:
                    today = datetime.now(timezone.utc).date()
                    if inventory.expiry_date < today:
                        days_expired = (today - inventory.expiry_date).days
                        raise ValueError(
                            f"Cannot use {ing.ingredient_name} - EXPIRED {days_expired} day{'s' if days_expired != 1 else ''} ago "
                            f"(expired on {inventory.expiry_date})"
                        )

                # Deduct from inventory directly
                inventory.current_quantity = float(current_qty - qty_in_inventory_unit)

                # Cost from inventory unit_cost
                unit_cost = Decimal(str(inventory.unit_cost)) if inventory.unit_cost else Decimal(0)
                cost = qty_in_inventory_unit * unit_cost
                total_cost += cost

                # Log consumption (no batch number for standalone)
                consumptions.append({
                    "ingredient_name": ing.ingredient_name,
                    "batch_number": "STANDALONE",                    # ← no batch
                    "quantity_consumed": float(qty_in_inventory_unit),
                    "unit": inventory.unit,
                    "quantity_consumed_recipe_unit": float(
                        convert_quantity_unit(
                            value=qty_in_inventory_unit,
                            from_unit=inventory.unit,
                            to_unit=ing.unit
                        )
                    ),
                    "recipe_unit": ing.unit,
                    "cost": float(cost)
                })
        
        # Generate batch number for semi-finished product
        batch_number = f"SF_{product.name[:3].upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate expiry
        expiry_date = None
        if product.shelf_life_hours:
            expiry_date = datetime.now(timezone.utc) + timedelta(hours=product.shelf_life_hours)
        
        # Create stock batch
        stock = PrePreparedMaterialStock(
            tenant_id=tenant_id,
            product_id=product_id,
            batch_number=batch_number,
            quantity_produced=Decimal(str(quantity_to_produce)),
            quantity_remaining=Decimal(str(quantity_to_produce)),
            unit=product.unit,
            expiry_date=expiry_date,
            user_id=user_id,
            total_cost=total_cost
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
        
        return {
            "stock_id": stock.id,
            "batch_number": batch_number,
            "product_name": product.name,
            "quantity_produced": float(quantity_to_produce),
            "unit": product.unit,
            "total_cost": float(total_cost),
            "cost_per_unit": float(total_cost / Decimal(str(quantity_to_produce))),
            "expiry_date": expiry_date,
            "ingredients_consumed": consumptions
        }
    
    @staticmethod
    def get_available_semi_finished_stock(
        db: Session,
        tenant_id: UUID,
        product_id: UUID,
        quantity_required: float
    ) -> List[dict]:
        """Get available stock batches of semi-finished product (FIFO/FEFO)"""
        
        stocks = db.query(PrePreparedMaterialStock).filter(
            and_(
                PrePreparedMaterialStock.tenant_id == tenant_id,
                PrePreparedMaterialStock.product_id == product_id,
                PrePreparedMaterialStock.is_active == True,
                PrePreparedMaterialStock.quantity_remaining > 0
            )
        ).order_by(
            PrePreparedMaterialStock.expiry_date.asc().nullslast(),
            PrePreparedMaterialStock.production_date.asc()
        ).all()
        
        suggestions = []
        today = datetime.now(timezone.utc)
        
        for idx, stock in enumerate(stocks, start=1):
            hours_until_expiry = None
            is_near_expiry = False
            status = "FRESH"
            
            if stock.expiry_date:
                delta = stock.expiry_date - today
                hours_until_expiry = delta.days
                
                if hours_until_expiry < 0:
                    status = "EXPIRED"
                    is_near_expiry = True
                elif hours_until_expiry <= 2:  
                    status = "NEAR_EXPIRY"
                    is_near_expiry = True
            
            suggestions.append({
                "stock_id": stock.id,
                "batch_number": stock.batch_number,
                "quantity_remaining": float(stock.quantity_remaining),
                "unit": stock.unit,
                "production_date": stock.production_date,
                "expiry_date": stock.expiry_date,
                "hours_until_expiry": hours_until_expiry,
                "status": status,
                "is_near_expiry": is_near_expiry,
                "priority_rank": idx
            })
        
        return suggestions
    
class DishIngredientService:
    """Service for managing dish ingredients with FIFO/FEFO suggestions"""
    @staticmethod
    def get_fifo_fefo_batch_suggestions(
        db: Session,
        tenant_id: int,
        ingredient_id: int,
        quantity_required: float,
        unit: str
    ) -> Dict[str, any]:
        """
        Get FIFO/FEFO batch suggestions for ingredient
        """
        
        # Get inventory item
        inventory = db.query(Inventory).filter(
            and_(
                Inventory.tenant_id == tenant_id,
                Inventory.id == ingredient_id
            )
        ).first()
        
        if not inventory:
            return {
                "suggestions": [],
                "total_available": 0,
                "quantity_required": quantity_required,
                "can_fulfill": False,
                "shortage": quantity_required,
                "warnings": [f"Ingredient ID {ingredient_id} not found"],
                "allocation_plan": [],
                "near_expiry_count": 0,
                "expired_count": 0
            }
        
        # Get all available batches sorted by FEFO/FIFO
        batches = db.query(InventoryBatch).filter(
            and_(
                InventoryBatch.tenant_id == tenant_id,
                InventoryBatch.inventory_item_id == ingredient_id,
                InventoryBatch.is_active == True,
                InventoryBatch.quantity_remaining > 0
            )
        ).order_by(
            InventoryBatch.expiry_date.asc().nullslast(),
            InventoryBatch.created_at.asc()
        ).all()
        
        if not batches:
            return {
                "suggestions": [],
                "total_available": 0,
                "quantity_required": quantity_required,
                "can_fulfill": False,
                "shortage": quantity_required,
                "warnings": [f"No batches available for {inventory.name}"],
                "allocation_plan": [],
                "near_expiry_count": 0,
                "expired_count": 0
            }
        
        suggestions = []
        total_available = Decimal(0)
        warnings = []
        allocation_plan = []
        
        today = datetime.now().date()
        inventory_unit = inventory.unit


        quantity_needed_inventory = convert_quantity_unit(
            value=Decimal(str(quantity_required)),
            from_unit=unit,
            to_unit=inventory_unit
        )

        quantity_allocated = Decimal(0)
        
        near_expiry_count = 0
        expired_count = 0
        
        for idx, batch in enumerate(batches, start=1):
            # CRITICAL FIX: Handle Enum properly
            lifecycle_raw = batch.lifecycle_stage
            
            if lifecycle_raw is None:
                lifecycle_stage = ""
            elif isinstance(lifecycle_raw, Enum):
                # Extract Enum value: PerishableLifecycle.NEAR_EXPIRY -> "NEAR_EXPIRY"
                lifecycle_stage = lifecycle_raw.value.lower()
            elif isinstance(lifecycle_raw, str):
                lifecycle_stage = lifecycle_raw.strip().lower()
            else:
                lifecycle_stage = str(lifecycle_raw).strip().lower()
            
            # Calculate days until expiry
            days_until_expiry = None
            if batch.expiry_date:
                days_until_expiry = (batch.expiry_date - today).days
            
            # Determine flags based on NORMALIZED lifecycle_stage
            is_near_expiry = (lifecycle_stage == "near_expiry")
            is_expired = (lifecycle_stage == "expired")
            is_fresh = (lifecycle_stage == "fresh")
            
            # Update counts
            if is_near_expiry:
                near_expiry_count += 1
            if is_expired:
                expired_count += 1
            
            # Generate suggestion reason
            if is_expired:
                suggestion_reason = f"EXPIRED {abs(days_until_expiry) if days_until_expiry else 'unknown'} days ago - DO NOT USE"
            elif is_near_expiry:
                suggestion_reason = f"URGENT: Expires in {days_until_expiry} day{'s' if days_until_expiry != 1 else ''} - USE FIRST (FEFO)"
            elif is_fresh:
                if days_until_expiry:
                    suggestion_reason = f"Fresh batch - expires in {days_until_expiry} days"
                else:
                    suggestion_reason = "Fresh batch - no expiry date"
            else:
                # Fallback for unknown lifecycle or no expiry tracking
                if idx == 1:
                    suggestion_reason = "Oldest batch (FIFO) - no expiry tracking"
                else:
                    suggestion_reason = "Available batch - no expiry tracking"
            
            # Calculate allocation
            quantity_from_this_batch = Decimal(0)
            can_use_this_batch = not is_expired
            
            if can_use_this_batch and quantity_allocated < quantity_needed_inventory:
                remaining_needed = quantity_needed_inventory - quantity_allocated
                available_in_batch = Decimal(str(batch.quantity_remaining))
                quantity_from_this_batch = min(remaining_needed, available_in_batch)
                quantity_allocated += quantity_from_this_batch
                
                # Convert Enum to string for JSON serialization
                lifecycle_stage_str = lifecycle_raw.value if isinstance(lifecycle_raw, Enum) else lifecycle_raw
                
                allocation_plan.append({
                    "batch_id": batch.id,
                    "batch_number": batch.batch_number,
                    "quantity_to_use": float(quantity_from_this_batch),
                    "unit": inventory_unit,
                    "quantity_to_use_recipe_unit": float(           # also show in recipe unit
                        convert_quantity_unit(
                            value=quantity_from_this_batch,
                            from_unit=inventory_unit,
                            to_unit=unit
                        )
                    ),
                    "recipe_unit": unit,
                    "cost": float(quantity_from_this_batch * (batch.unit_cost or Decimal(0))),
                    "lifecycle_stage": lifecycle_stage_str,
                    "priority": idx,
                    "suggestion_reason": suggestion_reason
                })
                
                # Add warning for near-expiry batches being used
                if is_near_expiry:
                    warnings.append(
                        f"Using near-expiry batch {batch.batch_number} - expires in {days_until_expiry} day{'s' if days_until_expiry != 1 else ''}"
                    )
            
            # Track total available (excluding expired)
            if not is_expired:
                total_available +=  Decimal(str(batch.quantity_remaining))
            
            # Add expired warning
            if is_expired:
                warnings.append(
                    f"Batch {batch.batch_number} is EXPIRED - excluded from allocation"
                )
            
            # Convert Enum to string for JSON response
            lifecycle_stage_str = lifecycle_raw.value if isinstance(lifecycle_raw, Enum) else lifecycle_raw
            
            # Build suggestion
            suggestions.append(BatchInfo(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                expiry_date=batch.expiry_date,
                quantity_remaining=batch.quantity_remaining,
                days_until_expiry=days_until_expiry,
                lifecycle_stage=lifecycle_stage_str,  # String value, not Enum
                unit_cost=batch.unit_cost or Decimal(0),
                is_near_expiry=is_near_expiry,
                priority_rank=idx,
                suggestion_reason=suggestion_reason,
                allocated_quantity=float(quantity_from_this_batch) if quantity_from_this_batch > 0 else None
            ))
        
        # Check if we can fulfill
        can_fulfill = quantity_allocated >= quantity_needed_inventory
        shortage_inventory = quantity_needed_inventory - quantity_allocated if not can_fulfill else Decimal(0)

        shortage_recipe = float(
            convert_quantity_unit(
                value=shortage_inventory,
                from_unit=inventory_unit,
                to_unit=unit
            )
        ) if not can_fulfill else 0

        total_available_recipe = float(
            convert_quantity_unit(
                value=total_available,
                from_unit=inventory_unit,
                to_unit=unit
            )
        )


        # Add shortage warning
        if not can_fulfill:
            warnings.insert(0, 
                f"INSUFFICIENT QUANTITY: Need {quantity_required}{unit}, "
                f"Available {float(total_available_recipe)}{unit}, "
                f"Shortage: {shortage_recipe}{unit}"
            )
        
        # Add priority message for near-expiry batches
        # near_expiry_in_allocation = len([a for a in allocation_plan if is_near_expiry])
        
        if near_expiry_count > 0:
            allocated_near_expiry = sum(1 for s in suggestions if s.is_near_expiry and s.allocated_quantity)
            if allocated_near_expiry > 0:
                priority_msg = f"PRIORITY: {allocated_near_expiry} near-expiry batch{'es' if allocated_near_expiry > 1 else ''} should be used first (FEFO)"
                warnings.insert(0 if can_fulfill else 1, priority_msg)
        
        return {
            "ingredient_id": ingredient_id,
            "ingredient_name": inventory.name,
            "quantity_required": quantity_required,
            "unit": unit,
            "total_available": float(total_available),
            "can_fulfill": can_fulfill,
            "shortage": shortage_recipe,
            "quantity_allocated": float(
                convert_quantity_unit(
                    value=quantity_allocated,
                    from_unit=inventory_unit,
                    to_unit=unit
                )
            ),   
            "suggestions": suggestions,
            "allocation_plan": allocation_plan,
            "warnings": warnings,
            "near_expiry_count": near_expiry_count,
            "expired_count": expired_count
        }
 
    @staticmethod
    def _get_batch_suggestion_reason(
        lifecycle_stage: str,
        days_until_expiry: Optional[int],
        is_oldest: bool
    ) -> str:
        """Generate human-readable suggestion reason"""
        
        # FIX: Handle case-insensitive lifecycle stages
        lifecycle_lower = lifecycle_stage if lifecycle_stage else ""
        
        if lifecycle_lower == "expired":
            return f"EXPIRED {abs(days_until_expiry)} days ago - DO NOT USE"
        
        elif lifecycle_lower == "near_expiry":
            return f"URGENT: Expires in {days_until_expiry} days - USE FIRST (FEFO)"
        
        elif lifecycle_lower == "fresh":
            if days_until_expiry:
                return f"Fresh batch - expires in {days_until_expiry} days"
            else:
                return "Fresh batch - no expiry date"
        
        else:  # No expiry tracking
            if is_oldest:
                return "Oldest batch (FIFO) - no expiry tracking"
            else:
                return "Available batch - no expiry tracking"
            
    @staticmethod
    def add_ingredient_to_dish(
        db: Session,
        tenant_id: UUID,
        dish_id: int,
        ingredient_data: AddDishIngredient
    ) -> Tuple[DishIngredient, dict, str]:
        """
        Add ingredient to dish - supports both RAW and SEMI_FINISHED
        Returns: (dish_ingredient, batch/stock_info, message)
        """
        
        # Verify dish exists
        dish = db.query(Dish).filter(
            and_(Dish.tenant_id == tenant_id, Dish.id == dish_id)
        ).first()
        
        if not dish:
            raise ValueError("Dish not found")
        
        # Handle SEMI-FINISHED ingredients
        if ingredient_data.ingredient_type == DishIngredientType.SEMI_FINISHED:
            if not ingredient_data.preprepred_material_id:
                raise ValueError("semi_finished_product_id required for SEMI_FINISHED type")
            
            # Get semi-finished product
            product = db.query(PrePreparedMaterial).filter(
                and_(
                    PrePreparedMaterial.tenant_id == tenant_id,
                    PrePreparedMaterial.id == ingredient_data.preprepred_material_id
                )
            ).first()
            
            if not product:
                raise ValueError("Semi-finished product not found")
            
            qty_in_product_unit = convert_quantity_unit(
                value=Decimal(str(ingredient_data.quantity_required)),
                from_unit=ingredient_data.unit,    
                to_unit=product.unit                
            )
            
            # Get available stock
            stocks = SemiFinishedService.get_available_semi_finished_stock(
                db=db,
                tenant_id=tenant_id,
                product_id=product.id,
                quantity_required=float(qty_in_product_unit)
            )
            
            if not stocks:
                raise ValueError(f"No stock available for {product.name}. Please produce a batch first.")
            
            # Filter active stock
            active_stocks = [s for s in stocks if s["status"] != "EXPIRED"]
            if not active_stocks:
                raise ValueError(f"All stock of {product.name} is expired")
            
            selected_stock = active_stocks[0]  # Highest priority (FIFO/FEFO)
            
            if Decimal(str(selected_stock["quantity_remaining"])) < qty_in_product_unit:
                raise ValueError(
                    f"Insufficient {product.name}. "
                    f"Available: {selected_stock['quantity_remaining']} {product.unit}, "
                    f"Required: {float(qty_in_product_unit)} {product.unit}"
                )
            
            # Create dish ingredient record
            dish_ingredient = DishIngredient(
                tenant_id=tenant_id,
                dish_id=dish_id,
                ingredient_id=None,
                preprepred_material_id=product.id,
                is_semi_finished=True,
                quantity_required=ingredient_data.quantity_required,
                ingredient_name=product.name,
                unit=ingredient_data.unit,
                cost_per_unit=float(product.cost_per_unit or Decimal(0))
            )
            
            db.add(dish_ingredient)
            db.commit()
            db.refresh(dish_ingredient)
            
            message = f"Using semi-finished: {selected_stock['batch_number']}"
            if selected_stock["is_near_expiry"]:
                message += f" {selected_stock['status']}"
            
            return dish_ingredient, selected_stock, message
        
        # Handle RAW ingredients
        else:
            if not ingredient_data.ingredient_id:
                raise ValueError("ingredient_id required for RAW type")
            
            # Get ingredient (needed for unit and standalone fallback)
            ingredient = db.query(Inventory).filter(
                and_(Inventory.tenant_id == tenant_id, Inventory.id == ingredient_data.ingredient_id)
            ).first()
            
            if not ingredient:
                raise ValueError("Ingredient not found")
            
            qty_in_inventory_unit = convert_quantity_unit(
                value=Decimal(str(ingredient_data.quantity_required)),
                from_unit=ingredient_data.unit,
                to_unit=ingredient.unit
            )

            # Check if batches exist
            batches = db.query(InventoryBatch).filter(
                and_(
                    InventoryBatch.tenant_id == tenant_id,
                    InventoryBatch.inventory_item_id == ingredient_data.ingredient_id,
                    InventoryBatch.is_active == True,
                    InventoryBatch.quantity_remaining > 0
                )
            ).all()

            if batches:
        
                suggestions_result = DishIngredientService.get_fifo_fefo_batch_suggestions(
                    db=db,
                    tenant_id=tenant_id,
                    ingredient_id=ingredient_data.ingredient_id,
                    quantity_required=ingredient_data.quantity_required,
                    unit=ingredient_data.unit
                )

                suggestions = suggestions_result["suggestions"]
                
                if not suggestions_result["can_fulfill"]:
                    raise ValueError(
                        f"Insufficient quantity for {suggestions_result['ingredient_name']}. "
                        f"Required: {suggestions_result['quantity_required']}{suggestions_result['unit']}, "
                        f"Available: {suggestions_result['total_available']}{suggestions_result['unit']}, "
                        f"Shortage: {suggestions_result['shortage']}{suggestions_result['unit']}"
                    )

                # Filter out expired batches
                active_suggestions = [
                   s for s in suggestions if s.lifecycle_stage.upper() != "EXPIRED"
                ]         

                if not active_suggestions:
                    raise ValueError(f"All batches of {ingredient.name} are expired")
                
                # Use preferred batch or first suggestion
                if ingredient_data.preferred_batch_id:
                    selected = next((s for s in active_suggestions if s.batch_id == ingredient_data.preferred_batch_id), None)
                    if not selected:
                        raise ValueError("Preferred batch not available")
                    message = f"Using selected batch: {selected.batch_number}"
                else:
                    selected = active_suggestions[0]
                    message = f"Auto-selected: {selected.suggestion_reason}"
                
                # Check quantity
                if Decimal(str(selected.quantity_remaining)) < qty_in_inventory_unit:
                    raise ValueError(
                        f"Insufficient quantity in batch {selected.batch_number}. "
                        f"Available: {selected.quantity_remaining} {ingredient.unit}, "
                        f"Required: {float(qty_in_inventory_unit)} {ingredient.unit}"
                    )
                
                # Get batch record
                batch = db.query(InventoryBatch).filter(InventoryBatch.id == selected.batch_id).first()

                # Create transaction FIRST
                transaction = InventoryTransaction(
                    tenant_id=tenant_id,
                    inventory_item_id=ingredient_data.ingredient_id,
                    batch_id=batch.id,
                    transaction_type=TransactionType.PREPARATION,
                    quantity=Decimal(str(ingredient_data.quantity_required)),
                    unit_cost=batch.unit_cost,
                    total_value=qty_in_inventory_unit * (batch.unit_cost or Decimal(0)),  # converted unit
                )
                db.add(transaction)
                db.flush()

                unit_cost = batch.unit_cost or Decimal(0)
                batch_info = selected  # return BatchInfo object

            else:
                 # get element from direct inventory
                current_qty = Decimal(str(ingredient.current_quantity)) if ingredient.current_quantity else Decimal(0)

                if current_qty < qty_in_inventory_unit:
                    raise ValueError(
                        f"Insufficient {ingredient.name}. "
                        f"Available: {float(current_qty)} {ingredient.unit}, "
                        f"Required: {float(qty_in_inventory_unit)} {ingredient.unit}"
                    )
                
                if ingredient.expiry_date:
                    today = datetime.now(timezone.utc).date()
                    if ingredient.expiry_date < today:
                        days_expired = (today - ingredient.expiry_date).days
                        raise ValueError(
                            f"Cannot use {ingredient.name} - EXPIRED {days_expired} day{'s' if days_expired != 1 else ''} ago "
                            f"(expired on {ingredient.expiry_date})"
                        )

                # Create transaction without batch
                transaction = InventoryTransaction(
                    tenant_id=tenant_id,
                    inventory_item_id=ingredient_data.ingredient_id,
                    batch_id=None,
                    transaction_type=TransactionType.PREPARATION,
                    quantity=Decimal(str(ingredient_data.quantity_required)),
                    unit_cost=ingredient.unit_cost,
                    total_value=qty_in_inventory_unit * (ingredient.unit_cost or Decimal(0)),
                )
                db.add(transaction)
                db.flush()

                unit_cost = ingredient.unit_cost or Decimal(0)
                message = f"Using standalone inventory: {ingredient.name}"

                # Create a dict to match the batch_info structure
                batch_info = {
                    "batch_id": None,
                    "batch_number": "STANDALONE",
                    "quantity_remaining": float(current_qty),
                    "unit": ingredient.unit,
                    "lifecycle_stage": "STANDALONE",
                    "unit_cost": float(unit_cost),
                    "is_near_expiry": False,
                    "suggestion_reason": "Standalone inventory item (no batches)"
                }

            # NOW create dish_ingredient (transaction.id exists)
            dish_ingredient = DishIngredient(
                tenant_id=tenant_id,
                dish_id=dish_id,
                ingredient_id=ingredient_data.ingredient_id,
                preprepred_material_id=None,
                is_semi_finished=False,
                inventory_transaction_id=transaction.id,
                quantity_required=ingredient_data.quantity_required,
                ingredient_name=ingredient.name,
                unit=ingredient_data.unit,
                cost_per_unit=float(unit_cost)
            )

            # Update transaction with dish_ingredient reference
            transaction.dish_ingredient_id = dish_ingredient.id
            
            db.add(dish_ingredient)
            db.commit()
            db.refresh(dish_ingredient)
            
            return dish_ingredient, batch_info, message
    
    @staticmethod
    def add_multiple_ingredients(
        db: Session,
        tenant_id: int,
        dish_id: int,
        ingredients_list: List[AddDishIngredient]
    ) -> dict:
        """Add multiple ingredients to dish with FIFO/FEFO suggestions"""
        
        results = []
        successful = 0
        failed = 0
        near_expiry_count = 0
        
        for ingredient_data in ingredients_list:
            try:
                dish_ingredient, batch, message = DishIngredientService.add_ingredient_to_dish(
                    db=db,
                    tenant_id=tenant_id,
                    dish_id=dish_id,
                    ingredient_data=ingredient_data
                )
                
                if batch.is_near_expiry:
                    near_expiry_count += 1
                
                results.append({
                    "success": True,
                    "ingredient_id": dish_ingredient.id,
                    "ingredient_name": dish_ingredient.ingredient_name,
                    "batch_assigned": batch,
                    "message": message
                })
                successful += 1
                
            except ValueError as e:
                results.append({
                    "success": False,
                    "ingredient_id": ingredient_data.ingredient_id,
                    "error": str(e)
                })
                failed += 1
        
        warning = None
        if near_expiry_count > 0:
            warning = f"{near_expiry_count} ingredient(s) using near-expiry batches"
        
        return {
            "total": len(ingredients_list),
            "successful": successful,
            "failed": failed,
            "results": results,
            "warning": warning
        }

class DishPreparationService:

    @staticmethod
    def prepare_dish(
        db: Session,
        tenant_id: int,
        dish_id: int,
        quantity: int,
        user_id: int,
        notes: Optional[str] = None,
        batch_id: Optional[int] = None
    ) -> PreparationResult:
        """
        Prepare dish and automatically deduct inventory
        Supports both RAW ingredients and SEMI_FINISHED products
        """
        
        # Get dish
        dish = db.query(Dish).filter(
            and_(Dish.tenant_id == tenant_id, Dish.id == dish_id)
        ).first()
        
        if not dish:
            raise ValueError("Dish not found")
        
        # Get dish ingredients (both raw and semi-finished)
        dish_ingredients = db.query(DishIngredient).filter(
            and_(
                DishIngredient.tenant_id == tenant_id, 
                DishIngredient.dish_id == dish_id
            )
        ).all()
        
        #DEBUG: Log ingredient count
        print(f"Found {len(dish_ingredients)} ingredients for dish {dish_id}")
        
        if not dish_ingredients:
            raise ValueError("No ingredients configured for this dish")
        
        # Create preparation log
        prep_log = DishPreparationBatchLog(
            tenant_id=tenant_id,
            dish_id=dish_id,
            user_id=user_id,
            batch_id=batch_id,
            quantity_prepared=quantity,
            notes=notes,
            track_status=PreparationBatchStatus.IN_PROGRESS,
            inventory_deducted=False
        )
        db.add(prep_log)
        db.flush()
        
        total_cost = Decimal(0)
        consumptions = []
        
        # Process ALL ingredients first, then add to db
        for idx, dish_ing in enumerate(dish_ingredients):
            print(f"Processing ingredient {idx + 1}/{len(dish_ingredients)}: {dish_ing.ingredient_name}")
            print(f"   - Is semi-finished: {dish_ing.is_semi_finished}")
            print(f"   - Quantity required: {dish_ing.quantity_required}")
            
            qty_needed = Decimal(str(dish_ing.quantity_required)) * quantity
            print(f"   - Total quantity needed: {qty_needed}")
            
            # Check if semi-finished or raw ingredient
            if dish_ing.is_semi_finished:
               # lofic to add pre prepared material to dish
                print(f"   - Looking for semi-finished stock (product_id: {dish_ing.preprepred_material_id})")
                
                stocks = db.query(PrePreparedMaterialStock).filter(
                    and_(
                        PrePreparedMaterialStock.tenant_id == tenant_id,
                        PrePreparedMaterialStock.product_id == dish_ing.preprepred_material_id,
                        PrePreparedMaterialStock.is_active == True,
                        PrePreparedMaterialStock.quantity_remaining > 0
                    )
                ).order_by(
                    PrePreparedMaterialStock.expiry_date.asc().nullslast(),
                    PrePreparedMaterialStock.production_date.asc()
                ).all()
                
                print(f"   - Found {len(stocks)} semi-finished stocks")
                
                if not stocks:
                    raise ValueError(
                        f"No stock available for {dish_ing.ingredient_name}. "
                        f"Please produce a batch first."
                    )
                
                # Calculate total available
                total_available = sum(Decimal(str(s.quantity_remaining)) for s in stocks)
                print(f"   - Total available: {total_available}")
                
                if total_available < qty_needed:
                    raise ValueError(
                        f"Insufficient {dish_ing.ingredient_name}. "
                        f"Available: {float(total_available)} {dish_ing.unit}, "
                        f"Required: {float(qty_needed)} {dish_ing.unit}"
                    )
                
                # Allocate from stocks (FIFO/FEFO)
                qty_remaining = qty_needed
                
                for stock in stocks:
                    if qty_remaining <= 0:
                        break

                    stock_qty = Decimal(str(stock.quantity_remaining))

                    # How much to take from this stock
                    qty_from_stock = min(stock_qty, qty_remaining)
                    print(f"   - Taking {qty_from_stock} from stock {stock.batch_number}")
                    
                    # DEDUCT FROM SEMI-FINISHED STOCK
                    stock.quantity_remaining = float(stock_qty - qty_from_stock)
                    
                    # Calculate cost
                    if stock.quantity_produced and stock.quantity_produced > 0 and stock.total_cost:
                        cost_per_unit = Decimal(str(stock.total_cost)) / Decimal(str(stock.quantity_produced))
                    else:
                        cost_per_unit = Decimal(0)
                        print(f"WARNING: Stock {stock.batch_number} has zero cost!")
                        
                    cost = qty_from_stock * cost_per_unit
                    total_cost += cost
                    
                    print(f"   - Cost per unit: {cost_per_unit}, Total cost: {cost}")
                    
                    # Create consumption record
                    consumption = PreparationIngredientHistory(
                        tenant_id=tenant_id,
                        preparation_log_id=prep_log.id,
                        ingredient_id=None,
                        batch_id=None,
                        preprepred_material_id=stock.product_id,
                        ingredient_name=dish_ing.ingredient_name,
                        batch_number=stock.batch_number,
                        quantity_consumed=float(qty_from_stock),
                        unit=dish_ing.unit,
                        cost_per_unit=float(cost_per_unit),
                        total_cost=float(cost)
                    )
                    db.add(consumption)
                    
                    consumptions.append({
                        "ingredient_name": dish_ing.ingredient_name,
                        "ingredient_type": "SEMI_FINISHED",
                        "batch_number": stock.batch_number,
                        "quantity_consumed": float(qty_from_stock),
                        "unit": dish_ing.unit,
                        "cost": float(cost),
                        "cost_per_unit": float(cost_per_unit),
                        "remaining_in_stock": float(stock.quantity_remaining)
                    })
                    
                    qty_remaining -= qty_from_stock
                
            else:
               # logic to add raw ingredients
                print(f"   - Looking for raw ingredient batches (ingredient_id: {dish_ing.ingredient_id})")
                
                # Get available batches (FIFO/FEFO sorted)
                batches = db.query(InventoryBatch).filter(
                    and_(
                        InventoryBatch.tenant_id == tenant_id,
                        InventoryBatch.inventory_item_id == dish_ing.ingredient_id,
                        InventoryBatch.is_active == True,
                        InventoryBatch.quantity_remaining > 0
                    )
                ).order_by(
                    InventoryBatch.expiry_date.asc().nullslast(),
                    InventoryBatch.created_at.asc()
                ).all()
                
                print(f"   - Found {len(batches)} raw ingredient batches")
                
                if not batches:
                    raise ValueError(f"No batches available for {dish_ing.ingredient_name}")
                
                # Calculate total available
                total_available = sum(Decimal(str(b.quantity_remaining)) for b in batches)
                print(f"   - Total available: {total_available}")
                
                if total_available < qty_needed:
                    raise ValueError(
                        f"Insufficient {dish_ing.ingredient_name}. "
                        f"Available: {float(total_available)} {dish_ing.unit}, "
                        f"Required: {float(qty_needed)} {dish_ing.unit}"
                    )
                
                # Allocate from batches (FIFO/FEFO)
                qty_remaining = qty_needed
                
                for batch in batches:
                    if qty_remaining <= 0:
                        break
                    
                    # Convert to Decimal for precise calculation
                    batch_qty_remaining = Decimal(str(batch.quantity_remaining))
                    batch_unit_cost = Decimal(str(batch.unit_cost)) if batch.unit_cost else Decimal(0)
                    
                    # How much to take from this batch
                    qty_from_batch = min(batch_qty_remaining, qty_remaining)
                    print(f"   - Taking {qty_from_batch} from batch {batch.batch_number}")
                    
                    # DEDUCT FROM BATCH
                    batch.quantity_remaining = float(batch_qty_remaining - qty_from_batch)
                    
                    # Calculate cost
                    cost = qty_from_batch * batch_unit_cost
                    total_cost += cost
                    
                    if batch_unit_cost == 0:
                        print(f"WARNING: Batch {batch.batch_number} has zero unit cost!")
                    
                    print(f"   - Unit cost: {batch_unit_cost}, Total cost: {cost}")
                    
                    # Create consumption record
                    consumption = PreparationIngredientHistory(
                        tenant_id=tenant_id,
                        preparation_log_id=prep_log.id,
                        ingredient_id=dish_ing.ingredient_id,
                        batch_id=batch.id,
                        ingredient_name=dish_ing.ingredient_name,
                        batch_number=batch.batch_number,
                        quantity_consumed=float(qty_from_batch),
                        unit=dish_ing.unit,
                        cost_per_unit=float(batch_unit_cost),
                        total_cost=float(cost)
                    )
                    db.add(consumption)
                    
                    consumptions.append({
                        "ingredient_name": dish_ing.ingredient_name,
                        "ingredient_type": "RAW",
                        "batch_number": batch.batch_number,
                        "quantity_consumed": float(qty_from_batch),
                        "unit": dish_ing.unit,
                        "cost": float(cost),
                        "cost_per_unit": float(batch_unit_cost),
                        "remaining_in_batch": float(batch.quantity_remaining)
                    })
                    
                    qty_remaining -= qty_from_batch
                
                # DEDUCT FROM INVENTORY TOTAL
                inventory = db.query(Inventory).filter(Inventory.id == dish_ing.ingredient_id).first()
                if inventory:
                    current_qty = Decimal(str(inventory.current_quantity)) if inventory.current_quantity else Decimal(0)
                    inventory.current_quantity = float(current_qty - qty_needed)
        
        print(f"Total cost calculated: {total_cost}")
        print(f"Total consumptions: {len(consumptions)}")
        
        # Update preparation log AFTER processing all ingredients
        prep_log.total_cost = float(total_cost)
        prep_log.inventory_deducted = True
        prep_log.track_status = PreparationBatchStatus.IN_PROGRESS

        # Update batch if applicable
        if batch_id:
            prep_batch = db.query(DishPreparationBatch).filter(
                DishPreparationBatch.id == batch_id
            ).first()
            if prep_batch:
                prep_batch.total_dishes_completed += quantity
                existing_cost = Decimal(str(prep_batch.total_cost)) if prep_batch.total_cost else Decimal(0)
                prep_batch.total_cost = float(existing_cost + total_cost)
        
        # Commit ONCE at the end
        db.commit()
        db.refresh(prep_log)
        
        # Return the actual consumptions list
        return PreparationResult(
            preparation_log_id=prep_log.id,
            dish_id=dish_id,
            dish_name=dish.name,
            quantity_prepared=quantity,
            ingredients_consumed=consumptions,
            total_cost=float(total_cost),
            inventory_deducted=True,
            preparation_date=prep_log.preparation_date
        )
    
    @staticmethod
    def prepare_multiple_dishes_batch(
        db: Session,
        tenant_id: int,
        preparations: List[SingleDishPreparation],
        user_id: int,
        batch_notes: Optional[str] = None
    ) -> BatchPreparationResult:
        """
        Prepare multiple dishes simultaneously in one batch
        """
        
        # Generate batch number
        batch_number = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
        
        total_planned = sum((p.quantity for p in preparations),Decimal(0))
        
        # Create batch record
        prep_batch = DishPreparationBatch(
            tenant_id=tenant_id,
            batch_number=batch_number,
            user_id=user_id,
            status=PreparationBatchStatus.IN_PROGRESS,
            total_dishes_planned=total_planned,
            total_dishes_completed=0,
            total_cost=Decimal(0),
            notes=batch_notes
        )
        db.add(prep_batch)
        db.flush()
        
        results = []
        warnings = []
        successful = 0
        failed = 0
        
        for prep in preparations:
            try:
                result = DishPreparationService.prepare_dish(
                    db=db,
                    tenant_id=tenant_id,
                    dish_id=prep.dish_id,
                    quantity=prep.quantity,
                    user_id=user_id,
                    notes=prep.notes,
                    batch_id=prep_batch.id
                )
                results.append(result)
                successful += 1
                
            except ValueError as e:
                warnings.append(f"Dish {prep.dish_id}: {str(e)}")
                failed += 1
        
        # Update batch status
        if successful == len(preparations):
            prep_batch.status = PreparationBatchStatus.COMPLETED
        else:
            prep_batch.status = PreparationBatchStatus.CANCELLED
        
        prep_batch.completed_at = datetime.now()
        
        db.commit()
        db.refresh(prep_batch)
        
        # Calculate duration
        duration = None
        if prep_batch.completed_at:
            delta = prep_batch.completed_at - prep_batch.started_at
            duration = int(delta.total_seconds() / 60)
        
        return BatchPreparationResult(
            batch_id=prep_batch.id,
            batch_number=prep_batch.batch_number,
            status=prep_batch.status.value,
            total_dishes_prepared=prep_batch.total_dishes_completed,
            successful=successful,
            failed=failed,
            total_cost=float(prep_batch.total_cost),
            started_at=prep_batch.started_at,
            completed_at=prep_batch.completed_at,
            duration_minutes=duration,
            preparations=results,
            warnings=warnings
        )
    
    @staticmethod
    def get_preparation_history(
        db: Session,
        tenant_id: int,
        dish_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get preparation history with filters"""
        
        query = db.query(DishPreparationBatchLog).filter(
            DishPreparationBatchLog.tenant_id == tenant_id
        )
        
        if dish_id:
            query = query.filter(DishPreparationBatchLog.dish_id == dish_id)
        if user_id:
            query = query.filter(DishPreparationBatchLog.user_id == user_id)
        if start_date:
            query = query.filter(DishPreparationBatchLog.preparation_date >= start_date)
        if end_date:
            query = query.filter(DishPreparationBatchLog.preparation_date <= end_date)
        
        logs = query.order_by(DishPreparationBatchLog.preparation_date.desc()).limit(limit).all()
        
        results = []
        for log in logs:
            dish = db.query(Dish).filter(Dish.id == log.dish_id).first()
            user = db.query(User).filter(User.id == log.user_id).first()
            
            consumptions = db.query(PreparationIngredientHistory).filter(
                PreparationIngredientHistory.preparation_log_id == log.id
            ).all()
            
            batch_number = None
            if log.batch_id:
                batch = db.query(DishPreparationBatch).filter(
                    DishPreparationBatch.id == log.batch_id
                ).first()
                if batch:
                    batch_number = batch.batch_number
            
            results.append({
                "id": log.id,
                "dish_name": dish.name if dish else "Unknown",
                "quantity_prepared": log.quantity_prepared,
                "user_name": user.full_name if user else "Unknown",
                "preparation_date": log.preparation_date,
                "batch_number": batch_number,
                "notes": log.notes,
                "total_cost": float(log.total_cost),
                "inventory_deducted": log.inventory_deducted,
                "ingredients_consumed": [
                    {
                        "ingredient_name": c.ingredient_name,
                        "batch_number": c.batch_number,
                        "quantity_consumed": float(c.quantity_consumed),
                        "unit": c.unit,
                        "cost": float(c.total_cost)
                    }
                    for c in consumptions
                ]
            })
        
        return results