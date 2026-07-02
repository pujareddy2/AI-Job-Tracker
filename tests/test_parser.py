"""
tests/test_parser.py — Unit Tests for resume_parser/parser.py
=============================================================
Tests verify:
  1. Parsing of a specific resume file path using legacy ResumeParser.
  2. Exception raised if path does not exist.
  3. Dict returned has personal name and parsed data categories.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from resume_parser.parser import ResumeParser
from utils.exceptions import ResumeParserError


def test_resume_parser_nonexistent_file() -> None:
    parser = ResumeParser(Path("resume/nonexistent_xyz.pdf"))
    with pytest.raises(ResumeParserError):
        parser.parse()


def test_resume_parser_run(tmp_path: Path) -> None:
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text(
        "MIDDE SRAVYA\nEmail: sravya@test.com\nEDUCATION\nB.Tech\nSKILLS\nPython\n",
        encoding="utf-8"
    )

    parser = ResumeParser(resume_file)
    data = parser.parse()
    
    assert isinstance(data, dict)
    assert data["personal"]["name"] == "MIDDE SRAVYA"
    assert "Python" in data["skills"]["programming_languages"]
