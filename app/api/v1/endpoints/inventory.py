"""
app/api/v1/endpoints/inventory.py
Inventory management endpoints
"""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query , status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel
from app.api.deps import get_db
from app.models.expense import Expense
from app.models.inventory import Inventory, InventoryBatch, InventoryTransaction,ItemCategory, StorageLocation, TransactionType
from app.models.users import User
from app.schemas.batch import BatchCreate
from app.schemas.inventory import InventoryListResponse, InventoryOut, InventoryResponse,InventoryUpdate,InventoryItemCreate, ItemCategoryListResponseAll, ItemCategoryOut,ItemPerishableNonPerishable,ItemCategoryCreate,ItemCategoryUpdate,ItemCategoryResponse
from app.services.inventory_service import InventoryService
from app.schemas.inventory_storage import StorageLocationCreate,StorageLocationUpdate,StorageLocationResponse
from app.utils.auth_helper import get_current_user,get_tanant_scope
from app.schemas.common import ApiResponse
from app.utils.inventory_batch_helper import calculate_days_until_expiry, determine_lifecycle_stage, generate_batch_number_sequential
from app.utils.response_helper import success_response
from app.tasks import update_batch_lifecycles_status

router = APIRouter()

class StorageLocationCreateResponse(BaseModel):
    status_code: int
    message: str
    location: StorageLocationResponse
    

#INVENTORY-ITEM API's
@router.post("/add_item", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    item: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )

    if item.price_per_unit is not None:
        total_cost = item.quantity * item.price_per_unit
        price_per_unit = item.price_per_unit
    elif total_cost is not None:
        total_cost = item.total_cost
        # price_per_unit = 0.0
        price_per_unit = (
            total_cost / item.quantity if item.quantity > 0 else 0
        )      
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Either price_per_unit or total_cost must be provided"
        )
    
    try:

        category = (
            db.query(ItemCategory).filter(
                ItemCategory.id == item.item_category_id,
                ItemCategory.tenant_id == current_user.tenant_id,
            ).first()
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item category not found",
            ) 
        
        storage_location = (
            db.query(StorageLocation)
            .filter(
                StorageLocation.id == item.storage_location_id,
                StorageLocation.tenant_id == current_user.tenant_id,
            )
            .first()
        )

        if not storage_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage location not found",
            )
        
        inventory_item = Inventory(
            user_id = current_user.id,
            tenant_id=current_user.tenant_id,
            storage_location_id=item.storage_location_id,
            item_category_id=item.item_category_id,
            name=item.name,
            sku=item.sku,
            quantity=item.quantity,
            current_quantity=item.quantity,                     # ← added: initialize from quantity
            unit=item.unit,
            price_per_unit=price_per_unit,
            unit_cost=price_per_unit,
            total_cost=total_cost,
            type=item.type or "",
            reorder_point=item.reorder_point,
            expiry_date=item.expiry_date,
            purchase_unit=item.purchase_unit,
            purchase_unit_size=item.purchase_unit_size,
            shelf_life_in_days=item.shelf_life_in_days,
            date_added=item.date_added or datetime.utcnow(),
        )

        db.add(inventory_item)

        expense = Expense(
            tenant_id=current_user.tenant_id,
            item_name=item.name,
            quantity=item.quantity,
            total_cost=total_cost,
            date=item.date_added or datetime.utcnow(),
        )
        db.add(expense)

        db.commit()
        db.refresh(inventory_item)

        return {
            "success": True,
            "message": "Inventory item added successfully",
            "data": inventory_item,
        }
    
    except HTTPException as e:
        print(e,"PRINT")
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print("ERROR",e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add inventory item",
        )
    
@router.get("/", response_model=InventoryListResponse)
def get_all_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required"
        )
    
    try:
       inventory =( db.query(Inventory).filter(Inventory.tenant_id == current_user.tenant_id).all())

       return {
            "success": True,
            "message": "Inventory fetched successfully",
            "data": inventory,
       }
    except HTTPException:
        raise

    except Exception as e:
        print("GET INVENTORY", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inventory",
        )

@router.get("/search", response_model=InventoryListResponse, status_code=status.HTTP_200_OK)
def search_inventory(
    name: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )
    
    try:

        service = InventoryService(db)
        inventory = service.search_items (
            tenant_id=current_user.tenant_id,
            name=name,
            type=type,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "success": True,
            "message": "Inventory search completed",
            "data": inventory,
        }
    
    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search inventory",
        )

@router.put("/{item_id}", response_model=InventoryResponse, status_code=status.HTTP_200_OK)
def update_inventory_item(
    item_id: int,
    item_update: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    
    try:
        service = InventoryService(db)
        updated_item = service.update_item( 
            item_id=item_id,
            tenant_id=current_user.tenant_id,
            item_update=item_update,
            )
        
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        
        return {
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Inventory item updated successfully",
            "data": updated_item,
        }
    except HTTPException as e:
        return {
            "success": False,
            "status_code": e.status_code,
            "message": e.detail,
        }

    except Exception:
        return {
            "success": False,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Failed to update inventory item",
        }

@router.delete("/{item_id}")
def delete_inventory_item(
    item_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ):

    if not current_user.tenant_id:
        return {
            "success": False,
            "status_code": status.HTTP_403_FORBIDDEN,
            "message": "Tenant access required",
        }

    try:
        service = InventoryService(db)
        success = service.delete_item(
            item_id=item_id,
            tenant_id=current_user.tenant_id,
        )

        if not success:
            return {
                "success": False,
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Inventory item not found",
            }

        return {
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Inventory item deleted successfully",
        }

    except Exception:
        return {
            "success": False,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Failed to delete inventory item",
        }


@router.delete("/")
def delete_all_inventory(
    confirm: bool = Query(False, description="Confirm deletion"),
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    
    if not current_user.tenant_id:
        return {
            "success": False,
            "status_code": status.HTTP_403_FORBIDDEN,
            "message": "Tenant access required",
        }
    """Delete all inventory items (use with caution)"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm deletion by setting confirm=true"
        )
    
    service = InventoryService(db)
    deleted_count = service.delete_all_items()
    return {
        "message": f"Deleted {deleted_count} item(s) from inventory"
    }


#ITEM-CATEGORIES API'S
@router.post("/add-item-category",response_model=ItemCategoryResponse)
def create_item_category(
    data: ItemCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)

):
    # if not current_user.tenant_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Tenant access required",
    #     )

    tenant_id = get_tanant_scope(
        current_user=current_user,
        requested_tenant_id=data.tenant_id
)
    
    try:
        category_type_enum = ItemPerishableNonPerishable(data.category_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category_type: {data.category_type}",
        )
    
    print(f"DEBUG - Enum name: {category_type_enum.name}")  # Should print "PERISHABLE"
    print(f"DEBUG - Enum value: {category_type_enum.value}")  
    
    existing =( db.query(ItemCategory).filter(
        ItemCategory.name == data.name,
        ItemCategory.tenant_id == tenant_id,
    ).first() )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Category with this name already exists"
        )
    try:
        
        category = ItemCategory(
            tenant_id=tenant_id,
            name=data.name,
            category_type=category_type_enum.value,
            user_id=current_user.id
        )

        db.add(category)
        db.commit()
        db.refresh(category)

        return success_response(
        data=category,
        message="Item category created successfully",
        # status_code=status.HTTP_201_CREATED,
    )
    
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item category",
        )

@router.get("/get-item-categories")
def list_item_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print("HELLO")
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    try:
        categories = (
            db.query(ItemCategory)
            # .filter(ItemCategory.tenant_id == current_user.tenant_id)
            .order_by(ItemCategory.name)
            .all()
    )


        return {
                "success": True,
                "status_code": 200,
                "message": "Item categories fetched successfully",
                "data": categories
            } 
     
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch item categories",
        )   


@router.get("/{item_id}", response_model=InventoryResponse,status_code=status.HTTP_200_OK)
def get_inventory_item(
    item_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ):

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    try:
        service = InventoryService(db)
        item = service.get_item_by_id(
            item_id=item_id,
            tenant_id=current_user.tenant_id,
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        
        return {
            "success": True,
            "message": "Inventory item fetched successfully",
            "data": item,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inventory item",
        )


@router.get("/get-category-id/{category_id}",response_model=ItemCategoryResponse,status_code=status.HTTP_200_OK)
def get_item_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    
    try:
        category = (
             db.query(ItemCategory)
            .filter(
                ItemCategory.id == category_id,
                ItemCategory.tenant_id == current_user.tenant_id,
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item category not found",
            )
        
        return {
            "success": True,
            "message": "Item category fetched successfully",
            "data": category,
            "status_code":status.HTTP_200_OK,
        }
   
    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch item category",
        )

@router.put("/update-item-category/{category_id}", response_model=ItemCategoryResponse)
def update_item_category(
    category_id: int,
    data: ItemCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    
    category = (
        db.query(ItemCategory).filter(
            ItemCategory.id == category_id,
            ItemCategory.tenant_id == current_user.tenant_id
        ).first()
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Item Category not found"
        )
    try:

        if data.name is not None:
        
            existing =(
               db.query(ItemCategory).filter(ItemCategory.name == data.name,
                    ItemCategory.tenant_id == current_user.tenant_id,
                    ItemCategory.id != category_id,).first()
            )
            if existing:
               raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists",
                )
            category.name = data.name


        if data.category_type is not None:
            try:
                category.category_type = ItemPerishableNonPerishable(data.category_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category_type: {data.category_type}",
                )
            
       
        db.commit()
        db.refresh(category)

        return {
            "success": True,
            "message": "Item category updated successfully",
            "data": category,
        }
    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item category",
        )

@router.delete("/delete-item-categories/{category_id}",status_code=status.HTTP_200_OK)
def delete_item_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    if not current_user.tenant_id:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required",
        )
    
    try:
        category = (db.query(ItemCategory).filter(
                ItemCategory.id == category_id
            ).first())  

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Item category not found"
            )
        
        if category.inventory_items:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category with inventory items",
            )
        
        db.delete(category)
        db.commit()

        return {
                "success": True,
                "message": "Item category deleted successfully",
            }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item category",
        )
    

#STORAGE LOCATION API's
@router.post("/add-storage",response_model=StorageLocationCreateResponse,status_code=status.HTTP_201_CREATED)
def add_storage_location(
    data: StorageLocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    tenant_id = get_tanant_scope(
        current_user=current_user,
        requested_tenant_id=data.tenant_id  
    )
    try:

        existing = db.query(StorageLocation).filter(
            StorageLocation.tenant_id == current_user.tenant_id,
            StorageLocation.name == data.name,
            StorageLocation.is_active == True
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage location with this name already exists."
            )
        
        location = StorageLocation(
            tenant_id=tenant_id,
            user_id=current_user.id,
            name=data.name,
            storage_temp_min=data.storage_temp_min,
            storage_temp_max=data.storage_temp_max,
            special_handling_instructions=data.special_handling_instructions,
            is_active=True
        )

        db.add(location)
        db.commit()
        db.refresh(location)

        result = update_batch_lifecycles_status.delay()


        return {
            "data": {
                "status": status.HTTP_201_CREATED,
                "message": "Storage location added successfully!",
                "location": location,
                "result": result.id
            }
        }
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Storage location could not be created due to a database constraint"
        )
        
    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create storage location"
        )
    
@router.get("/get-all-storage", response_model=list[StorageLocationResponse])
def get_storage_locations (
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        locations = db.query(StorageLocation).filter(
                StorageLocation.tenant_id == current_user.tenant_id,
                StorageLocation.is_active == True
            ).offset(skip).limit(limit).all()
       
        return {
            "data": {
                "status": status.HTTP_200_OK,
                "message": "Storage locations fetched successfully",
                "storage_locations": locations
            }
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fresh storage locations"
        )    
    
@router.get("/storage-id/{location_id}",response_model=StorageLocationResponse)
def get_location_by_id(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        location = db.query(StorageLocation).filter(
                StorageLocation.id == location_id,
                StorageLocation.tenant_id == current_user.tenant_id,
                StorageLocation.is_active == True
            ).first()

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage location not found"
            )

        return {
            "data": {
                "status": status.HTTP_200_OK,
                "message": "Storage location fetched successfully",
                "location": location
            }
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch storage location"
        )

@router.put("/update-storage/{location_id}", response_model=StorageLocationResponse)
def update_location(
    location_id: int,
    data: StorageLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        location = db.query(StorageLocation).filter(
            StorageLocation.id == location_id,
            StorageLocation.tenant_id == current_user.tenant_id
        ).first()

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage location not found"
            )

        # Prevent renaming to existing name
        if data.name:
            duplicate = db.query(StorageLocation).filter(
                StorageLocation.tenant_id == current_user.tenant_id,
                StorageLocation.name == data.name,
                StorageLocation.id != location_id,
                StorageLocation.is_active == True
            ).first()

            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Storage location with this name already exists"
                )

        for field, value in data.dict(exclude_unset=True).items():
            setattr(location, field, value)

        db.commit()
        db.refresh(location)
        return {
            "data": {
                "status": status.HTTP_200_OK,
                "message": "Storage location updated successfully",
                "location": location
            }
        }

    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update violates a database constraint"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update storage location"
        )

@router.delete("/delete-storage-id/{location_id}", response_model=StorageLocationResponse)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        location = db.query(StorageLocation).filter(
            StorageLocation.id == location_id,
            StorageLocation.tenant_id == current_user.tenant_id
        ).first()

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage location not found"
            )

        location.is_active = False
        db.commit()
        db.refresh(location)
        return {
            "data": {
                "status": status.HTTP_200_OK,
                "message": "Storage location deleted successfully",
                "location": location
            }
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete storage location"
        )
    
#INVENTORY BATCH API's
@router.post("/items/{item_id}/batches")
def create_batch(
    item_id: int,
    batch_data: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:

        item = (db.query(Inventory).filter(Inventory.id == item_id).filter(Inventory.tenant_id ==current_user.tenant_id).first())
        print(item,"ITEMMMMM")

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        if not batch_data.quantity_received:
               raise HTTPException(status_code=400, detail="quantity_received is required")

        if not batch_data.unit_cost:
                raise HTTPException(status_code=400, detail="unit_cost is required")

        if not batch_data.expiry_date:
                raise HTTPException(status_code=400, detail="expiry_date is required")

        
        # if not item.is_perishable:
        #     raise HTTPException(
        #         status_code=400, 
        #         detail="This item is not marked as perishable"
        #     )

        # existing_batch = db.query(InventoryBatch)\
        #     .filter(InventoryBatch.inventory_item_id == item_id)\
        #     .filter(InventoryBatch.batch_number == batch_data.batch_number)\
        #     .first()
        
        days_until_expiry = calculate_days_until_expiry(batch_data.expiry_date)
        lifecycle = determine_lifecycle_stage(
            days_until_expiry,
            item.fresh_threshold_days or 3,
            item.near_expiry_threshold_days or 1
        )

        batch_number = generate_batch_number_sequential(
        item_id=item_id,
        db=db,
        prefix="BATCH"
        )

        batch = InventoryBatch(
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                inventory_item_id=item_id,
                batch_number=batch_number,
                expiry_date=batch_data.expiry_date,
                quantity_received=batch_data.quantity_received,
                quantity_remaining=batch_data.quantity_received,
                unit=batch_data.unit,
                packets=batch_data.packets,
                pieces=batch_data.pieces,
                total_pieces=batch_data.total_pieces,
                price_per_packet=batch_data.price_per_packet,
                price_per_piece=batch_data.price_per_piece,
                unit_cost=batch_data.unit_cost,
                lifecycle_stage=lifecycle,
                is_active=True
            )

        db.add(batch)
        db.flush()  # assigns batch.id
        
        current_qty = Decimal(str(item.current_quantity)) if item.current_quantity else Decimal(0)
        if item.expiry_date and item.expiry_date < date.today():
            # Standalone is expired, reset to only this batch
            print(f"{item.name} standalone stock expired on {item.expiry_date}, resetting quantity")
            item.current_quantity = float(Decimal(str(batch_data.quantity_received)))
        else:
            # Standalone is fresh or no expiry, add to existing
            item.current_quantity = float(current_qty + Decimal(str(batch_data.quantity_received)))
        
        item.unit_cost = batch_data.unit_cost

        transaction = InventoryTransaction(
                tenant_id=current_user.tenant_id,
                # branch_id=item.branch_id,
                inventory_item_id=item_id,
                batch_id=batch.id,
                transaction_type=TransactionType.PURCHASE,
                quantity=batch_data.quantity_received,
                unit_cost=batch_data.unit_cost,
                total_value=batch_data.quantity_received * batch_data.unit_cost,
                reference_id=f"Batch {batch.batch_number} received"
            )

        db.add(transaction)

        db.commit()

        return {
            "success": True,
            "message": "Batch created successfully",
            "batch_id": batch.id,
            "lifecycle_stage": lifecycle.value,
            "days_until_expiry": days_until_expiry
        }
      
    except HTTPException:
        raise
    except Exception as e:
        print("PRINTTT", e)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



