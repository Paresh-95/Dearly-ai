import re

# Deliberately conservative (prefers false positives over missed
# detections): a wrongly-triggered safety message costs nothing, a missed
# one could cost everything. This is a fast first layer, not a clinical
# assessment — it exists to make sure a real resource is surfaced, not to
# judge intent.
_CRISIS_PATTERNS = [
    r"\bkill(?:ing)? myself\b",
    r"\bend(?:ing)? my (?:own )?life\b",
    r"\bsuicid\w*\b",
    r"\bwant(?:ed)? to die\b",
    r"\bdon'?t want to (?:live|be alive) anymore\b",
    r"\bself[\s-]?harm\w*\b",
    r"\bhurt(?:ing)? myself\b",
    r"\bno reason to live\b",
    r"\bcan'?t go on\b",
    r"\bbetter off (?:dead|without me)\b",
]
_CRISIS_RE = re.compile("|".join(_CRISIS_PATTERNS), re.IGNORECASE)

CRISIS_RESOURCE_TEXT = (
    "If you're in India, the KIRAN mental health helpline is free and "
    "available any time, day or night, at 1800-599-0019. If you're "
    "somewhere else, please reach out to a crisis line in your country, or "
    "go to your nearest emergency room. You don't have to go through this "
    "alone."
)


def detect_crisis_risk(text: str) -> bool:
    return bool(_CRISIS_RE.search(text))


# A backstop for the model inventing its own hotline/number despite being
# told not to — some base models override system-prompt instructions with
# their own built-in safety response when they perceive risk. Prompting
# alone can't guarantee compliance, so any reply containing resource-shaped
# content is treated as untrusted and replaced with the verified text,
# regardless of why the model produced it.
_RESOURCE_LEAK_PATTERNS = [
    r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b",
    r"\b(?:911|999|988|112|116\s?123)\b",
    r"\bhotline\b",
    r"\bhelpline\b",
    r"\bcrisis\s?line\b",
    r"\bemergency\s?(?:services|department|room)\b",
    r"findahelpline",
]
_RESOURCE_LEAK_RE = re.compile("|".join(_RESOURCE_LEAK_PATTERNS), re.IGNORECASE)


def contains_self_generated_resource(text: str) -> bool:
    return bool(_RESOURCE_LEAK_RE.search(text))


FALLBACK_SAFE_REPLY = (
    "I'm really glad you told me. I care about you and I want you to be okay."
)
