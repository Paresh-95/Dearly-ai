import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.tools.web_search import format_search_results, search_web

logger = logging.getLogger(__name__)

# Groq exposes an OpenAI-compatible chat completions endpoint; embeddings
# still go through OpenAI directly (see app/rag/embeddings.py) since Groq
# doesn't serve an embeddings API.
_client = AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.llm_base_url)

_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web for general, current, or factual information you "
            "don't already know for certain — practical how-to info, current "
            "events, local resources, definitions, etc. Never use this for "
            "anything about your own biography, life, or relationships — "
            "those must come only from retrieved memories, never a search."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A concise search query"}},
            "required": ["query"],
        },
    },
}

async def generate_reply(system_prompt: str, memory_block: str, history: list[dict], user_text: str) -> str:
    messages = [{"role": "system", "content": f"{system_prompt}\n\n{memory_block}"}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    response = await _client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.4,
    )
    return response.choices[0].message.content or ""


async def generate_reply_with_search(
    system_prompt: str, memory_block: str, history: list[dict], user_text: str
) -> str:
    """Same as generate_reply, but first offers the model a web-search tool.
    If it calls one, results are folded into plain context for a single
    clean final completion — rather than keeping raw tool-call messages in
    history for a second tool-enabled round, which some providers (Groq's
    gpt-oss-120b included) keep re-triggering tool use on even with
    tool_choice="none", causing a 400 once the round budget runs out.
    One search round is also simply enough for this use case.
    """
    messages = [{"role": "system", "content": f"{system_prompt}\n\n{memory_block}"}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    response = await _client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=[_SEARCH_TOOL],
        temperature=0.4,
    )
    message = response.choices[0].message
    if not message.tool_calls:
        return message.content or ""

    search_notes = []
    for tool_call in message.tool_calls:
        query = ""
        try:
            query = json.loads(tool_call.function.arguments).get("query", "")
        except Exception:
            logger.exception("Could not parse search tool arguments")
        results = await search_web(query) if query else []
        search_notes.append(f"Query: {query}\n{format_search_results(results)}")

    search_block = (
        "You already searched the web for this — no search tool is available "
        "anymore, so do not attempt to call one; answer now using the results "
        "below in your own words, naturally, not recited verbatim:\n"
        + "\n\n".join(search_notes)
    )
    final_messages = [{"role": "system", "content": f"{system_prompt}\n\n{memory_block}\n\n{search_block}"}]
    final_messages.extend(history)
    final_messages.append({"role": "user", "content": user_text})

    final = await _client.chat.completions.create(
        model=settings.llm_model,
        messages=final_messages,
        temperature=0.4,
    )
    return final.choices[0].message.content or ""
