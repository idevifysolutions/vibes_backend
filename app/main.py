from fastapi import FastAPI
from app.api.v1.routers import api_router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="Restaurant Inventory API")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(api_router, prefix="/api/v1")
