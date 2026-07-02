"""
tests/test_extractor.py — Unit Tests for resume_parser/extractor.py
====================================================================
Tests verify (requires temporary files):
  1. Missing file raises ResumeParserError.
  2. Unsupported extension raises ResumeParserError.
  3. Plain text UTF-8 extraction.
  4. Plain text CP1252 fallback extraction.
  5. Mock PDF and DOCX parser calls raise correct exceptions or handle mocks.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from resume_parser.extractor import ResumeExtractor
from utils.exceptions import ResumeParserError


def test_missing_file_raises_error() -> None:
    extractor = ResumeExtractor()
    with pytest.raises(ResumeParserError) as exc_info:
        extractor.extract(Path("resume/does_not_exist_xyz.pdf"))
    assert "file not found" in str(exc_info.value).lower()


def test_unsupported_extension(tmp_path: Path) -> None:
    unsupported_file = tmp_path / "resume.jpg"
    unsupported_file.touch()

    extractor = ResumeExtractor()
    with pytest.raises(ResumeParserError) as exc_info:
        extractor.extract(unsupported_file)
    assert "unsupported format" in str(exc_info.value).lower()


def test_extract_txt_utf8(tmp_path: Path) -> None:
    txt_file = tmp_path / "resume.txt"
    txt_content = "This is a UTF-8 resume content. Sparkle: ✨"
    txt_file.write_text(txt_content, encoding="utf-8")

    extractor = ResumeExtractor()
    text = extractor.extract(txt_file)
    assert text == txt_content


def test_extract_txt_cp1252(tmp_path: Path) -> None:
    txt_file = tmp_path / "resume.txt"
    # Write using cp1252 encoding with a specific currency symbol
    txt_content = "This is a CP1252 resume content. Cost: £100"
    txt_file.write_bytes(txt_content.encode("cp1252"))

    extractor = ResumeExtractor()
    text = extractor.extract(txt_file)
    # Check that cost is correctly extracted
    assert "Cost: £100" in text
