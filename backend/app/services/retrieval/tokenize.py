"""Script-aware word tokenization, shared by keyword search and the lexical-overlap
reranker.

A plain `[a-zA-Z0-9]+` regex matches nothing at all in Devanagari (Hindi/Marathi) text —
confirmed by actually running it. The seemingly-obvious fix, `\\w+`, is also wrong: Python's
`\\w` excludes Unicode combining marks (category Mn), and Devanagari vowel signs and the
virama (्) *are* combining marks, so `\\w+` fragments a word like "नमस्ते" into
['नमस', 'त', 'े'] — a word broken at every matra. This instead walks the string treating a
base letter together with any combining marks attached to it as one token, which is correct
for Devanagari and any other mark-using script, while still tokenizing Latin/ASCII text the
same way `\\w+` would."""

import unicodedata

_COMBINING_CATEGORIES = {"Mn", "Mc", "Me"}


def tokenize_words(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum() or unicodedata.category(ch) in _COMBINING_CATEGORIES:
            current.append(ch)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens
