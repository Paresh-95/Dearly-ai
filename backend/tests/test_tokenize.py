from app.services.retrieval.tokenize import tokenize_words


def test_splits_latin_text_like_a_word_regex_would():
    assert tokenize_words("Mum always made poha, every Sunday!") == [
        "Mum", "always", "made", "poha", "every", "Sunday",
    ]


def test_does_not_fragment_devanagari_words_at_combining_marks():
    """Confirms the actual bug: a naive [a-zA-Z0-9]+ matches nothing in Devanagari, and a
    naive \\w+ fragments words at every vowel sign/virama (both verified by hand before this
    tokenizer was written)."""
    assert tokenize_words("नमस्ते मुझे पोहा बहुत पसंद है") == [
        "नमस्ते", "मुझे", "पोहा", "बहुत", "पसंद", "है",
    ]


def test_marathi_sentence():
    assert tokenize_words("आई नेहमी रविवारी पोहे बनवत असे.") == [
        "आई", "नेहमी", "रविवारी", "पोहे", "बनवत", "असे",
    ]


def test_mixed_script_text():
    assert tokenize_words("मिश्रित Hindi and English मिश्रित वाक्य 123") == [
        "मिश्रित", "Hindi", "and", "English", "मिश्रित", "वाक्य", "123",
    ]


def test_empty_and_punctuation_only_input():
    assert tokenize_words("") == []
    assert tokenize_words("... ! ,  ।") == []
