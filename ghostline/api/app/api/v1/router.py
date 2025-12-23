from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    billing,
    files,
    generation,
    projects,
    source_materials,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    generation.router, prefix="/projects", tags=["generation"]
)
api_router.include_router(
    source_materials.router, prefix="/source-materials", tags=["source-materials"]
)
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
