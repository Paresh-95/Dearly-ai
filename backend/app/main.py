from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, memories, people, personas, sessions, voice_samples
from app.core.config import settings
from app.db.seed import ensure_admin_user
from app.db.session import SessionLocal, init_db
from app.storage.object_storage import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as db:
        await ensure_admin_user(db)
    ensure_bucket()
    yield


app = FastAPI(title="AI Memorial Persona API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(personas.router)
app.include_router(memories.router)
app.include_router(people.router)
app.include_router(voice_samples.router)
app.include_router(sessions.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
