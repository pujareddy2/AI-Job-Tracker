"""
tests/test_detector.py — Unit Tests for resume_parser/detector.py
===================================================================
Tests verify (requires temporary file structure):
  1. Empty directory raises ResumeParserError.
  2. Detector successfully locates files with supported extensions (.pdf, .docx, .txt).
  3. Detector ignores unsupported file extensions.
  4. Detector selects the newest file by modification time (mtime).
  5. list_all() returns candidates sorted newest-first.
  6. has_resume() returns correct boolean.
"""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from resume_parser.detector import ResumeDetector
from utils.exceptions import ResumeParserError


def test_empty_directory_raises_error(tmp_path: Path) -> None:
    detector = ResumeDetector(resume_dir=tmp_path)
    with pytest.raises(ResumeParserError) as exc_info:
        detector.find_newest()
    assert "no resume files found" in str(exc_info.value).lower()


def test_detector_locates_files(tmp_path: Path) -> None:
    # Create test files
    pdf_file = tmp_path / "resume1.pdf"
    pdf_file.touch()

    docx_file = tmp_path / "resume2.docx"
    docx_file.touch()

    detector = ResumeDetector(resume_dir=tmp_path)
    assert detector.has_resume() is True
    
    all_files = detector.list_all()
    assert len(all_files) == 2


def test_detector_ignores_unsupported_extensions(tmp_path: Path) -> None:
    unsupported_file = tmp_path / "resume.jpg"
    unsupported_file.touch()

    detector = ResumeDetector(resume_dir=tmp_path)
    assert detector.has_resume() is False
    with pytest.raises(ResumeParserError):
        detector.find_newest()


def test_detector_finds_newest_by_mtime(tmp_path: Path) -> None:
    # Create older file
    old_file = tmp_path / "older_resume.pdf"
    old_file.touch()

    # Artificially set back time
    old_mtime = time.time() - 3600
    import os
    os.utime(old_file, (old_mtime, old_mtime))

    # Create newer file
    new_file = tmp_path / "newest_resume.pdf"
    new_file.touch()

    detector = ResumeDetector(resume_dir=tmp_path)
    newest = detector.find_newest()
    assert newest.name == "newest_resume.pdf"

    # Verify sorting
    all_sorted = detector.list_all()
    assert all_sorted[0].name == "newest_resume.pdf"
    assert all_sorted[1].name == "older_resume.pdf"
