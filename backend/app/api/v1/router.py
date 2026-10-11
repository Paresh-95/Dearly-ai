from fastapi import APIRouter

from app.api.v1 import (
    auth,
    consents,
    conversations,
    health,
    ingestion_jobs,
    memories,
    profiles,
    retrieval,
    sources,
    uploads,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profiles.router)
api_router.include_router(memories.router)
api_router.include_router(consents.router)
api_router.include_router(uploads.router)
api_router.include_router(sources.router)
api_router.include_router(ingestion_jobs.router)
api_router.include_router(retrieval.router)
api_router.include_router(conversations.router)
