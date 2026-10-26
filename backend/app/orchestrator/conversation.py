import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.safety import (
    CRISIS_RESOURCE_TEXT,
    FALLBACK_SAFE_REPLY,
    contains_self_generated_resource,
    detect_crisis_risk,
)
from app.db.models import ConversationSession, ConversationTurn, Persona
from app.llm.llm_client import generate_reply, generate_reply_with_search
from app.llm.prompt_builder import (
    CRISIS_SYSTEM_PROMPT,
    SEARCH_TOOL_NOTE,
    build_memory_block,
    build_people_block,
    build_recent_usage_note,
    build_system_prompt,
    extract_mood_tag,
    get_signature_phrases,
)
from app.rag.retriever import find_mentioned_people, retrieve_relevant_chunks
from app.storage.object_storage import save_bytes
from app.voice.providers.deepgram_provider import DeepgramTranscriber
from app.voice.providers.fish_audio_provider import FishAudioVoiceProvider
from app.voice.providers.sarvam_provider import SarvamVoiceProvider
from app.voice.text_cleanup import clean_for_speech, strip_emoji

logger = logging.getLogger(__name__)

_transcriber = DeepgramTranscriber()
_fish_audio_provider = FishAudioVoiceProvider()
_sarvam_provider = SarvamVoiceProvider()

_MAX_HISTORY_TURNS = 10


def _active_voice(persona: Persona) -> tuple[object, str] | None:
    """Which voice provider + voice id to synthesize with for this persona,
    switchable per-persona via `voice_provider` without touching code —
    `provider_voice_id` (Fish Audio) stays intact even while Sarvam is
    active, so switching back later doesn't lose it.
    """
    if persona.voice_provider == "sarvam" and persona.sarvam_voice_id:
        return _sarvam_provider, persona.sarvam_voice_id
    if persona.voice_provider == "fish_audio" and persona.provider_voice_id:
        return _fish_audio_provider, persona.provider_voice_id
    return None


async def handle_turn(
    db: AsyncSession,
    session: ConversationSession,
    persona: Persona,
    audio_bytes: bytes,
    content_type: str,
) -> dict:
    user_text = await _transcriber.transcribe(audio_bytes, content_type, language=persona.language)
    if not user_text.strip():
        user_text = "(inaudible)"

    return await _handle_turn_text(db, session, persona, user_text)


async def handle_text_turn(
    db: AsyncSession,
    session: ConversationSession,
    persona: Persona,
    user_text: str,
) -> dict:
    return await _handle_turn_text(db, session, persona, user_text)


async def _handle_turn_text(
    db: AsyncSession,
    session: ConversationSession,
    persona: Persona,
    user_text: str,
) -> dict:
    history_stmt = (
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session.id)
        .order_by(ConversationTurn.created_at.desc())
        .limit(_MAX_HISTORY_TURNS)
    )
    prior_turns = list(reversed((await db.execute(history_stmt)).scalars().all()))
    history = [{"role": t.role, "content": t.text} for t in prior_turns]

    retrieved_chunk_ids: list[str] = []
    mood: str | None = None

    if detect_crisis_risk(user_text):
        # A dedicated, narrow prompt instead of the normal grounded/advice
        # pipeline — the model's only job here is a short in-character
        # expression of concern; the actual resource is appended verbatim
        # below rather than trusted to the model, so a hallucinated phone
        # number can never reach someone in crisis.
        crisis_prompt = CRISIS_SYSTEM_PROMPT.format(
            name=persona.name, relationship=persona.relationship_to_user or "a loved one"
        )
        reply_text = await generate_reply(crisis_prompt, "", history, user_text)
        reply_text = f"{reply_text.strip()}\n\n{CRISIS_RESOURCE_TEXT}"
    else:
        chunks = await retrieve_relevant_chunks(db, persona.id, user_text)
        mentioned_people = await find_mentioned_people(db, persona.id, user_text)
        retrieved_chunk_ids = [str(c.id) for c in chunks]

        recent_assistant_texts = [t.text for t in prior_turns if t.role == "assistant"][-2:]
        signature_phrases = get_signature_phrases(persona)
        usage_note = build_recent_usage_note(signature_phrases, recent_assistant_texts)

        system_prompt = build_system_prompt(persona) + usage_note
        memory_block = build_memory_block(chunks)
        people_block = build_people_block(mentioned_people)
        if people_block:
            memory_block += "\n\n" + people_block

        reply_text = await generate_reply_with_search(
            system_prompt + SEARCH_TOOL_NOTE, memory_block, history, user_text
        )

        if contains_self_generated_resource(reply_text):
            # The model named a hotline/number on its own despite being told
            # not to — never let an unverified number through; swap in the
            # one resource text we control instead of trusting the model's.
            reply_text = f"{FALLBACK_SAFE_REPLY}\n\n{CRISIS_RESOURCE_TEXT}"

        mood, reply_text = extract_mood_tag(reply_text)

    reply_audio_path: str | None = None
    audio_error: str | None = None
    active_voice = _active_voice(persona)
    if active_voice:
        voice_provider, voice_id = active_voice
        try:
            speech_text = clean_for_speech(reply_text)
            if persona.voice_provider == "sarvam":
                speech_text = strip_emoji(speech_text)
            audio = await voice_provider.synthesize(speech_text, voice_id, language=persona.language, mood=mood)
            reply_audio_path = save_bytes(f"replies/{session.id}", "mp3", audio)
        except Exception as exc:
            # Voice synthesis is a nice-to-have on top of the reply itself —
            # if the TTS provider fails, still return the text reply instead
            # of discarding a turn the LLM already generated successfully.
            # The detailed exception is logged server-side only; the client
            # gets a short, generic, non-sensitive reason.
            logger.exception("Voice synthesis failed for persona %s; returning text-only reply", persona.id)
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                audio_error = "Voice reply unavailable — usage limit reached. Showing text only."
            else:
                audio_error = "Voice reply unavailable right now. Showing text only."

    db.add(
        ConversationTurn(
            session_id=session.id,
            role="user",
            text=user_text,
            retrieved_memory_ids=[],
        )
    )
    assistant_turn = ConversationTurn(
        session_id=session.id,
        role="assistant",
        text=reply_text,
        retrieved_memory_ids=retrieved_chunk_ids,
        audio_path=reply_audio_path,
    )
    db.add(assistant_turn)
    await db.commit()
    await db.refresh(assistant_turn)

    return {
        "transcript": user_text,
        "reply_text": reply_text,
        "turn_id": str(assistant_turn.id),
        "has_audio": reply_audio_path is not None,
        "audio_error": audio_error,
    }
