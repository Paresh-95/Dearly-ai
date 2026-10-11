# ADR 0008 — Script-aware tokenization for keyword search and reranking

**Status:** accepted

The brief asks for multi-language support, "especially Hindi, Marathi and other languages."
Checking that against the actual retrieval code (not just assuming it would work) found two
real bugs, confirmed by hand before fixing either:

1. `app/services/retrieval/keyword.py` built its OR-combined keyword query with
   `re.findall(r"[a-zA-Z0-9]+", query)`. Run against a Devanagari query, that returns `[]` —
   not "some words missed," *zero* words extracted, so a pure-Hindi or pure-Marathi
   question matched nothing at all, unconditionally, regardless of what was approved.
2. The seemingly obvious fix, `\w+`, is also wrong. Python's `\w` excludes Unicode
   combining marks (category `Mn`), and Devanagari vowel signs and the virama (्) *are*
   combining marks — confirmed with `unicodedata.category()`. `\w+` on "नमस्ते" ("hello")
   returns `['नमस', 'त', 'े']`: a word fragmented at every matra, not a correctly
   tokenized one.

**Decision:** `app/services/retrieval/tokenize.py#tokenize_words` instead walks the string
treating a base letter together with any combining marks attached to it as one token
(`ch.isalnum() or unicodedata.category(ch) in {"Mn", "Mc", "Me"}`). Checked directly against
Postgres: `to_tsvector('simple', ...)` already tokenizes Devanagari into whole-word lexemes
correctly on its own (Postgres's parser is Unicode-aware) — the bug was entirely on the
Python side, in how the *query* was split into words before being OR-joined into a
`to_tsquery` string. Both `keyword.py` and the `LexicalOverlapReranker` now use this
tokenizer. `evals/datasets/retrieval_queries.json` has two Marathi/Hindi cases that
exercise it against the real database, not just unit tests.

**Also fixed as part of the same pass:**
- `app/services/chunking/chunker.py`'s sentence-boundary regex required a Latin capital
  letter after `.`/`!`/`?` to count as a split point, so Hindi/Marathi text — no case
  distinction, and often terminated with the danda (।) rather than a period — was never
  split into multiple sentences at all, always becoming one chunk regardless of length. The
  terminator class now includes `।`/`॥`, and the lookahead accepts a following Devanagari
  letter as well as a Latin capital.
- OCR (`app/services/extraction/image.py`) called `pytesseract.image_to_string(image)` with
  no `lang=`, which defaults to English only. `MC_OCR_LANGUAGES` (default `eng+hin+mar`) is
  now passed through, and the backend/worker Docker image installs
  `tesseract-ocr-hin`/`tesseract-ocr-mar` alongside the base package. Verified for real, not
  just by reasoning about it: built the image, confirmed `tesseract --list-langs` reports
  `eng hin mar`, rendered a Devanagari test image, and ran it through the actual
  `extract_image()` code path inside the container — it came back with the correct text.
- Every LLM-facing prompt (Milestone 3's candidate extractor, Milestone 6's answer
  generator, Milestone 7's interviewer) now says explicitly: write/answer in the same
  language the source material or question is in, never auto-translate into English, and
  never translate a quotation — copy it verbatim in its original script. `PersonProfile.
  languages` (already collected at onboarding) is passed into these prompts so the model
  expects the content's actual language(s) rather than defaulting to English.

**Deliberately not done:** translating the frontend's own UI strings (buttons, labels,
onboarding copy) into Hindi/Marathi. The request was about the RAG pipeline handling
multilingual *memory content* correctly, which is what this ADR covers; full UI
localization is a separate, much larger undertaking (an i18n framework, translated strings
for every page, a language switcher) that would need its own scoping if wanted.
