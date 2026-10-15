from fastapi import APIRouter

from app.api.v1 import (
    admin_ops,
    admin_users,
    admin_vendors,
    auth,
    categories,
    customer,
    health,
    my_vendor,
    reports,
    shortlist,
    vendor_work,
    vendors,
)

api_router = APIRouter()
# Public
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.public_router)
api_router.include_router(vendors.router)
# Signed-in users
api_router.include_router(reports.router)
api_router.include_router(shortlist.router)
api_router.include_router(customer.router)
api_router.include_router(my_vendor.router)
api_router.include_router(vendor_work.router)
# Administrators
api_router.include_router(categories.admin_router)
api_router.include_router(admin_vendors.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_ops.router)
