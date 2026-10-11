from app.services.chunking.chunker import chunk_memory

SHORT_KWARGS = {
    "quotations": [],
    "category": "family",
    "date_text": "1998",
    "location": "Goa",
    "people": ["Priya"],
    "max_chars": 1200,
}


def test_short_memory_stays_as_a_single_chunk():
    chunks = chunk_memory(
        title="Sunday breakfast",
        description="Mum always made poha every Sunday morning.",
        **SHORT_KWARGS,
    )
    assert len(chunks) == 1
    assert chunks[0].text.startswith("Sunday breakfast")
    assert "poha" in chunks[0].text


def test_chunk_metadata_carries_structured_fields():
    chunks = chunk_memory(title="T", description="D.", **SHORT_KWARGS)
    assert chunks[0].metadata == {
        "title": "T",
        "category": "family",
        "date_text": "1998",
        "location": "Goa",
        "people": ["Priya"],
    }


def test_quotations_are_kept_whole_and_appended():
    kwargs = {**SHORT_KWARGS, "quotations": ["Chalo, chalo!"]}
    chunks = chunk_memory(title="T", description="D.", **kwargs)
    assert len(chunks) == 1
    assert '"Chalo, chalo!"' in chunks[0].text


def test_long_description_splits_on_sentence_boundaries_never_mid_sentence():
    sentences = [f"This is sentence number {i} in a long family story." for i in range(40)]
    description = " ".join(sentences)
    kwargs = {**SHORT_KWARGS, "max_chars": 300}
    chunks = chunk_memory(title="A long memory", description=description, **kwargs)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.startswith("A long memory")
        # every sentence appears intact somewhere in this chunk or another -- never cut mid-way
        for s in sentences:
            if s in chunk.text:
                assert chunk.text.count(s) == 1

    rejoined = " ".join(c.text.removeprefix("A long memory\n\n").strip() for c in chunks)
    for s in sentences:
        assert s in rejoined


def test_quotations_land_on_the_last_chunk_of_a_long_memory():
    sentences = [
        f"Sentence {i} about the trip to the farm every summer holiday." for i in range(30)
    ]
    description = " ".join(sentences)
    kwargs = {**SHORT_KWARGS, "max_chars": 300, "quotations": ["Don't forget your umbrella"]}
    chunks = chunk_memory(title="Farm visits", description=description, **kwargs)

    assert len(chunks) > 1
    quote_chunks = [c for c in chunks if "Don't forget your umbrella" in c.text]
    assert len(quote_chunks) == 1
    assert quote_chunks[0] is chunks[-1]


def test_no_chunk_exceeds_the_configured_budget_by_much():
    sentences = [f"Sentence number {i} is reasonably short." for i in range(50)]
    description = " ".join(sentences)
    kwargs = {**SHORT_KWARGS, "max_chars": 200}
    chunks = chunk_memory(title="Short title", description=description, **kwargs)
    for chunk in chunks[:-1]:  # the last chunk may carry trailing quotations/overflow
        assert len(chunk.text) <= 260  # budget + title prefix, with slack for one sentence
