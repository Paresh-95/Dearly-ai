from openai import AsyncOpenAI

from app.core.config import settings

# OpenRouter exposes an OpenAI-compatible API, including /embeddings for
# models that support it — routed here instead of a model-specific SDK.
_client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.embedding_base_url,
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "AI Memorial Persona (MVP)",
    },
)


async def embed_text(text: str) -> list[float]:
    response = await _client.embeddings.create(model=settings.embedding_model, input=text)
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    response = await _client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]
