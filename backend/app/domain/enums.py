from enum import StrEnum


class MemoryStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class MemoryOrigin(StrEnum):
    USER_WRITTEN = "user_written"
    EXTRACTED = "extracted"
    INTERVIEW = "interview"
    QUESTIONNAIRE = "questionnaire"


class Provenance(StrEnum):
    """Whose voice a memory/source represents. Never inferred from diarisation alone."""

    DIRECT_RECORDING = "direct_recording"  # the person's own words
    FAMILY_RECOLLECTION = "family_recollection"  # someone else remembering
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class SourceKind(StrEnum):
    MANUAL = "manual"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    WHATSAPP = "whatsapp"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class ConversationKind(StrEnum):
    ASK = "ask"
    INTERVIEW = "interview"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConsentType(StrEnum):
    DATA_PROCESSING = "data_processing"
    EXTERNAL_AI_PROVIDER = "external_ai_provider"
    VOICE_SYNTHESIS = "voice_synthesis"  # reserved; no voice feature exists in this phase
