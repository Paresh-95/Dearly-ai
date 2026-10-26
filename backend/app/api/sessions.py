import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.personas import get_persona_or_404
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.models import ConversationSession, ConversationTurn
from app.db.session import get_db
from app.orchestrator.conversation import handle_text_turn, handle_turn
from app.storage.object_storage import read_bytes

router = APIRouter(tags=["sessions"], dependencies=[Depends(get_current_user)])

_ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
}
_MAX_TURN_AUDIO_BYTES = 15 * 1024 * 1024  # 15MB
_MAX_TURN_TEXT_CHARS = 4000


class SessionOut(BaseModel):
    id: uuid.UUID
    persona_id: uuid.UUID

    class Config:
        from_attributes = True


class TurnOut(BaseModel):
    transcript: str
    reply_text: str
    turn_id: str
    has_audio: bool
    audio_error: str | None = None


class TextTurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=_MAX_TURN_TEXT_CHARS)


class SessionSummaryOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    turn_count: int
    last_message: str | None


class TurnDetailOut(BaseModel):
    id: uuid.UUID
    role: str
    text: str
    has_audio: bool
    created_at: datetime


async def _get_session_or_404(session_id: uuid.UUID, db: AsyncSession) -> ConversationSession:
    session = await db.get(ConversationSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/personas/{persona_id}/sessions", response_model=SessionOut)
async def create_session(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ConversationSession:
    persona = await get_persona_or_404(persona_id, db)
    session = ConversationSession(persona_id=persona.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/personas/{persona_id}/sessions", response_model=list[SessionSummaryOut])
async def list_sessions(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    await get_persona_or_404(persona_id, db)

    sessions_stmt = (
        select(ConversationSession)
        .where(ConversationSession.persona_id == persona_id)
        .order_by(ConversationSession.started_at.desc())
    )
    sessions = (await db.execute(sessions_stmt)).scalars().all()
    if not sessions:
        return []

    session_ids = [s.id for s in sessions]
    counts_stmt = (
        select(ConversationTurn.session_id, func.count())
        .where(ConversationTurn.session_id.in_(session_ids))
        .group_by(ConversationTurn.session_id)
    )
    turn_counts = dict((await db.execute(counts_stmt)).all())

    last_message_stmt = (
        select(ConversationTurn.session_id, ConversationTurn.text)
        .where(ConversationTurn.session_id.in_(session_ids), ConversationTurn.role == "user")
        .order_by(ConversationTurn.session_id, ConversationTurn.created_at.desc())
    )
    last_messages: dict[uuid.UUID, str] = {}
    for session_id, text in (await db.execute(last_message_stmt)).all():
        last_messages.setdefault(session_id, text)

    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "turn_count": turn_counts.get(s.id, 0),
            "last_message": last_messages.get(s.id),
        }
        for s in sessions
        if turn_counts.get(s.id, 0) > 0
    ]


@router.get("/sessions/{session_id}/turns", response_model=list[TurnDetailOut])
async def list_turns(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[ConversationTurn]:
    await _get_session_or_404(session_id, db)
    turns_stmt = (
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.created_at.asc())
    )
    turns = (await db.execute(turns_stmt)).scalars().all()
    return [
        {
            "id": t.id,
            "role": t.role,
            "text": t.text,
            "has_audio": t.audio_path is not None,
            "created_at": t.created_at,
        }
        for t in turns
    ]


@router.post("/sessions/{session_id}/turns", response_model=TurnOut)
async def create_turn(
    session_id: uuid.UUID, audio: UploadFile, db: AsyncSession = Depends(get_db)
) -> dict:
    session = await _get_session_or_404(session_id, db)
    persona = await get_persona_or_404(session.persona_id, db)

    if audio.content_type not in _ALLOWED_AUDIO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    data = await audio.read(_MAX_TURN_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio")
    if len(data) > _MAX_TURN_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Audio clip too large")

    try:
        return await handle_turn(db, session, persona, data, audio.content_type)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to process conversation turn")


@router.post(
    "/sessions/{session_id}/turns/text",
    response_model=TurnOut,
    dependencies=[Depends(rate_limit(30))],
)
async def create_text_turn(
    session_id: uuid.UUID, payload: TextTurnIn, db: AsyncSession = Depends(get_db)
) -> dict:
    session = await _get_session_or_404(session_id, db)
    persona = await get_persona_or_404(session.persona_id, db)

    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        return await handle_text_turn(db, session, persona, user_text)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to process conversation turn")


@router.get("/sessions/{session_id}/turns/{turn_id}/audio")
async def get_turn_audio(session_id: uuid.UUID, turn_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    await _get_session_or_404(session_id, db)
    turn = await db.get(ConversationTurn, turn_id)
    if turn is None or turn.session_id != session_id or not turn.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    data = read_bytes(turn.audio_path)
    return Response(content=data, media_type="audio/mpeg")
