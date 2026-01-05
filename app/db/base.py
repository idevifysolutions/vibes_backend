"""
app/db/base.py
Import all models here for Alembic to detect them
"""
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

# Import all models here so Alembic can detect them
from app.models.inventory import Inventory  
from app.models.dish import Dish, DishType, DishIngredient  
from app.models.expense import Expense  
from app.models.logs import InventoryLog  
from app.models.branch import Branch
from app.models.users import User , UserBranchAccess