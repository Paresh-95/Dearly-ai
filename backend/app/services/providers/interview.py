"""The AI Memory Interviewer's question-asking side (brief §3 Method D). Turning the
resulting transcript into candidate memories reuses Milestone 3's
`MemoryCandidateExtractor` unchanged — see app/services/interview/pipeline.py — so this
module only covers deciding what to ask next."""

from abc import ABC, abstractmethod
from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings
from app.schemas.interview import InterviewTurn
from app.services.providers.errors import ProviderNotConfigured
from app.services.providers.generation import ConversationTurn

_SYSTEM_PROMPT = """\
You are conducting a gentle memory interview to help someone preserve memories of \
{display_name}, their {relationship}, who has died. Your only job is to ask good questions \
and listen — you are not answering anything or claiming any of your own memories of her.

Rules:
1. Ask exactly ONE question at a time, in `question`. Never ask two things at once.
2. Never lead the person or presuppose details that haven't been said yet. Do not ask \
"Did she enjoy baking?" (that assumes baking); ask something open like "What did she enjoy \
doing at home?" instead. Never suggest a fictional detail as if it might be true.
3. Use natural follow-ups grounded in what was just said, referring back to specifics they \
mentioned. Do not repeat a question already asked in this conversation.
4. Over the course of the interview, gently cover a mix of: her personality, her daily \
life and routines, family relationships and traditions, memorable events, and how she \
communicated (sayings, nicknames, tone). Do not announce these categories; just let the \
questions range naturally across them.
5. If the person's last answer says they want to stop, skip the rest, or are done (in any \
phrasing), set done to true, leave question empty, and write a short, warm thank-you in \
closing_message. Also set done to true, with a warm closing_message, once the conversation \
has covered good ground (roughly 8-12 exchanges) — do not drag it out.
6. Keep questions short, warm, and conversational — never clinical.
"""


class InterviewerQuestionGenerator(ABC):
    @abstractmethod
    def next_turn(
        self,
        *,
        display_name: str,
        relationship: str,
        history: list[ConversationTurn],
    ) -> InterviewTurn: ...


class OpenAIInterviewerQuestionGenerator(InterviewerQuestionGenerator):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def next_turn(
        self,
        *,
        display_name: str,
        relationship: str,
        history: list[ConversationTurn],
    ) -> InterviewTurn:
        transcript = "\n".join(f"{t.role}: {t.content}" for t in history) or "(nothing yet)"
        completion = self._client.chat.completions.parse(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT.format(
                        display_name=display_name, relationship=relationship
                    ),
                },
                {"role": "user", "content": f"Conversation so far:\n{transcript}"},
            ],
            response_format=InterviewTurn,
        )
        parsed = completion.choices[0].message.parsed
        return parsed or InterviewTurn(done=True, closing_message="Thank you for sharing.")


class FakeInterviewerQuestionGenerator(InterviewerQuestionGenerator):
    """Deterministic test double — never selected by configuration. Asks a fixed number of
    generic questions, then wraps up."""

    def __init__(self, max_questions: int = 3) -> None:
        self._max_questions = max_questions

    def next_turn(
        self,
        *,
        display_name: str,
        relationship: str,
        history: list[ConversationTurn],
    ) -> InterviewTurn:
        questions_asked = sum(1 for t in history if t.role == "assistant")
        if questions_asked >= self._max_questions:
            closing = f"Thank you for sharing about {display_name}."
            return InterviewTurn(done=True, closing_message=closing)
        question = f"Tell me more about {display_name}. (question {questions_asked + 1})"
        return InterviewTurn(question=question)


@lru_cache
def get_interviewer_question_generator() -> InterviewerQuestionGenerator:
    s = get_settings()
    if not s.openai_api_key:
        raise ProviderNotConfigured(
            "No LLM provider is configured (MC_OPENAI_API_KEY is unset), "
            "so the AI interviewer can't ask follow-up questions right now."
        )
    return OpenAIInterviewerQuestionGenerator(
        api_key=s.openai_api_key, base_url=s.openai_base_url, model=s.openai_chat_model
    )
