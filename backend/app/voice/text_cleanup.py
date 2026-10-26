import re

# Prompt instructions alone don't reliably keep the model from producing
# dashes/stacked punctuation (verified: it still slips through sometimes).
# This is a deterministic safety net applied only to the copy of the text
# sent to TTS — the stored/displayed reply is left untouched.
_DASH_RE = re.compile(r"\s*[—–]\s*")
_STACKED_TERMINAL_RE = re.compile(r"[.!?]{2,}")
_REPEATED_CHAR_RE = re.compile(r"([,.!?])\1+")
_COMMA_BEFORE_TERMINAL_RE = re.compile(r",\s*([.!?])")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")

# Fish Audio documents bracketed delivery cues and visibly vocalizes
# smiling/laughing emoji — intentional there. Sarvam's docs don't mention
# emoji at all; its text pipeline is built for Indic scripts + plain Latin
# text, and unsupported symbols are a likely cause of glitchy/"breaking"
# audio. Strip them only for providers that don't support them.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # misc symbols, pictographs, emoticons, transport, supplemental, extended-A
    "\U00002600-\U000027BF"  # misc symbols + dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators
    "\U0000FE0F"  # variation selector-16
    "\U0000200D"  # zero-width joiner
    "]+"
)


def clean_for_speech(text: str) -> str:
    """Normalize punctuation that tends to make TTS engines slur or stumble:
    em/en-dashes become a comma-pause, stacked terminal punctuation ("!?",
    "...") collapses to a single mark, and resulting double spaces/commas
    are tidied up.
    """
    text = _DASH_RE.sub(", ", text)
    text = _STACKED_TERMINAL_RE.sub(lambda m: m.group(0)[0], text)
    text = _REPEATED_CHAR_RE.sub(r"\1", text)
    text = _COMMA_BEFORE_TERMINAL_RE.sub(r"\1", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    return text.strip()


def strip_emoji(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    return _MULTI_SPACE_RE.sub(" ", text).strip()
