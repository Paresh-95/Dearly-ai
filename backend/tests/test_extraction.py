import os
from pathlib import Path

import pytest

from app.services.extraction.base import ExtractionError
from app.services.extraction.docx import extract_docx
from app.services.extraction.image import extract_image
from app.services.extraction.pdf import extract_pdf
from app.services.extraction.text import extract_text
from app.services.extraction.whatsapp import extract_whatsapp

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestTextExtractor:
    def test_splits_on_blank_lines_and_strips(self):
        segments = extract_text(_read("sample.txt"))
        assert [s.text for s in segments] == [
            "Sunday breakfast",
            "Mum always made poha every Sunday morning.",
            "She used to wake us up around eight.",
        ]

    def test_offsets_point_back_into_the_original_text(self):
        raw = _read("sample.txt").decode("utf-8")
        for seg in extract_text(_read("sample.txt")):
            assert raw[seg.char_start : seg.char_end] == seg.text

    def test_rejects_undecodable_bytes(self):
        with pytest.raises(ExtractionError):
            extract_text(b"\xff\xfe\x00\x01invalid")


class TestPdfExtractor:
    def test_one_segment_per_page_with_page_numbers(self):
        segments = extract_pdf(_read("sample.pdf"))
        assert [s.page for s in segments] == [1, 2]
        assert "Childhood summers" in segments[0].text
        assert "Page two" in segments[1].text

    def test_rejects_a_non_pdf(self):
        with pytest.raises(ExtractionError):
            extract_pdf(b"not actually a pdf")


class TestDocxExtractor:
    def test_one_segment_per_non_empty_paragraph(self):
        segments = extract_docx(_read("sample.docx"))
        assert [s.text for s in segments] == [
            "Family trip to Goa",
            "We went to Goa in 1998 and stayed by the beach for a week.",
        ]

    def test_rejects_a_non_docx(self):
        with pytest.raises(ExtractionError):
            extract_docx(b"not actually a docx")


class TestWhatsAppExtractor:
    def test_parses_sender_and_message(self):
        segments = extract_whatsapp(_read("sample_whatsapp.txt"))
        assert len(segments) == 3  # 3 real messages; the encrypted-notice line is skipped
        assert segments[0].speaker_label == "Asha"
        assert segments[0].speaker_verified is True
        assert segments[0].text == "Good morning!"
        assert segments[1].speaker_label == "Priya"

    def test_continuation_lines_are_appended_to_the_previous_message(self):
        segments = extract_whatsapp(_read("sample_whatsapp.txt"))
        third = next(s for s in segments if s.speaker_label == "Asha" and "umbrella" in s.text)
        assert third.text == "Don't forget your umbrella\nit looks like rain"

    def test_rejects_a_file_with_no_whatsapp_messages(self):
        with pytest.raises(ExtractionError):
            extract_whatsapp(_read("not_whatsapp.txt"))


class TestImageExtractor:
    def test_reads_dimensions_and_format_without_failing_when_ocr_is_unavailable(self):
        segments, metadata = extract_image(_read("sample.png"))
        assert metadata["width"] == 20 and metadata["height"] == 10
        assert metadata["format"] == "PNG"
        assert metadata["ocr_attempted"] is True
        # No text is a perfectly normal outcome for a plain image, not a failure.
        assert segments == [] or isinstance(segments[0].text, str)

    def test_rejects_a_non_image(self):
        with pytest.raises(ExtractionError):
            extract_image(b"not actually an image")


@pytest.mark.skipif(
    os.environ.get("MC_RUN_OCR_TESTS") != "1",
    reason="needs tesseract-ocr-hin/-mar installed locally; set MC_RUN_OCR_TESTS=1 "
    "(they're always present in the backend/worker Docker image)",
)
class TestDevanagariOcr:
    """Regression test for MC_OCR_LANGUAGES: pytesseract defaults to English-only OCR, so a
    Hindi/Marathi photo (e.g. of a handwritten note) silently produced no text at all until
    this was wired through. Skipped on the host (no tesseract installed); verified for
    real by hand against the built Docker image, which does have tesseract-ocr-hin/-mar
    installed (see infra/docker/backend.Dockerfile)."""

    def test_recognises_devanagari_text_in_an_image(self, tmp_path):
        import glob

        from PIL import Image, ImageDraw, ImageFont

        font_path = next(
            (
                p
                for p in glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
                if "devanagari" in p.lower() or "noto" in p.lower()
            ),
            None,
        )
        if font_path is None:
            pytest.skip("no Devanagari-capable font found on this system")

        img = Image.new("RGB", (600, 100), "white")
        ImageDraw.Draw(img).text(
            (10, 20), "नमस्ते पोहा", fill="black", font=ImageFont.truetype(font_path, 40)
        )
        path = tmp_path / "devanagari.png"
        img.save(path)

        segments, metadata = extract_image(path.read_bytes())
        assert metadata["ocr_available"] is True
        assert segments and "पोहा" in segments[0].text
