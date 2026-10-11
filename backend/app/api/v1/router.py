from fastapi import APIRouter

from app.api.v1 import auth, consents, health, memories, profiles

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profiles.router)
api_router.include_router(memories.router)
api_router.include_router(consents.router)
