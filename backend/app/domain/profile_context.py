"""A short, consistent description of the family member a memory/interview/conversation is
about, handed to every LLM provider that needs to know who the content is about. Shared by
Milestone 3 (candidate extraction), Milestone 7 (the interviewer), and anywhere else that
needs it, so the languages hint doesn't drift out of sync between them."""

from app.models import PersonProfile


def describe_profile(profile: PersonProfile) -> str:
    base = f"{profile.name} ({profile.relationship})"
    if profile.languages:
        # Told to the model so it recognises Hindi/Marathi/etc. content as expected, not as
        # something to silently translate into English (see the extraction/generation
        # system prompts' explicit language-preservation rules).
        base += f", who spoke {', '.join(profile.languages)}"
    return base
