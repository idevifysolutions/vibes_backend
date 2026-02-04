from fastapi import FastAPI
from app.api.v1.routers import api_router
from app.db.session import engine
from app.db.base import Base
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings 

app = FastAPI(title="Vibes Inventory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Base.metadata.create_all(bind=engine)    #only for inital develoment testing only
    pass

app.include_router(api_router, prefix="/api/v1")


#  if os.environ.get("DEV_MODE", "0") == "1":
#         # ONLY for local development
#         print("DEV_MODE=1 → Creating tables if missing (safe for dev only)")
#         Base.metadata.create_all(bind=engine)
#     else:
#         # Production: rely entirely on Alembic
#         print("Production mode → Skipping create_all() (Alembic handles migrations)")
