from fastapi import APIRouter

from app.api.v1 import admin_users, admin_vendors, auth, categories, health, my_vendor, vendors

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.public_router)
api_router.include_router(vendors.router)
api_router.include_router(my_vendor.router)
api_router.include_router(categories.admin_router)
api_router.include_router(admin_vendors.router)
api_router.include_router(admin_users.router)
