"""
app/api/v1/router.py
Main API router that aggregates all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    inventory,
    dishes,
    # preparation,
    # reports,
    # upload,
    # health
)
from app.api.v1.authentication import auth,tenant

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(inventory.router,prefix="/inventory", tags=["inventory"])

api_router.include_router( dishes.router, prefix="/dish",tags=["dish"])
api_router.include_router( auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenant.router, prefix="/tenant",tags=["Tenant"])

# api_router.include_router(
#     preparation.router,
#     prefix="/preparation",
#     tags=["preparation"]
# )

# api_router.include_router(
#     reports.router,
#     prefix="/reports",
#     tags=["reports"]
# )

# api_router.include_router(
#     upload.router,
#     prefix="/upload",
#     tags=["upload"]
# )

# api_router.include_router(
#     health.router,
#     prefix="/system",
#     tags=["system"]
# )