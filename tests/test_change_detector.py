"""
tests/test_change_detector.py — Unit Tests for resume_parser/change_detector.py
==============================================================================
Tests verify:
  1. ChangeDetector calculates correct file hashes.
  2. detect_changes() returns empty dict if old profile is missing.
  3. detect_changes() correctly lists added and removed skills, projects,
     certifications, and internships.
  4. detect_changes() returns empty dict if profiles are identical.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from resume_parser.profile_model import CandidateProfile, SkillsSection, Internship, Project
from resume_parser.change_detector import ResumeChangeDetector


def test_hash_calculation(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    
    detector = ResumeChangeDetector()
    h1 = detector.calculate_hash(test_file)
    h2 = detector.calculate_hash(test_file)
    assert h1 == h2

    # verify it matches standard SHA-256
    import hashlib
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert h1 == expected


def test_detect_changes_none_old_profile() -> None:
    detector = ResumeChangeDetector()
    new_profile = CandidateProfile()
    assert detector.detect_changes(None, new_profile) == {}


def test_detect_changes_identical() -> None:
    detector = ResumeChangeDetector()
    profile = CandidateProfile(
        skills=SkillsSection(programming_languages=["Python"]),
        certifications=["AWS"]
    )
    assert detector.detect_changes(profile, profile) == {}


def test_detect_changes_semantic_diff() -> None:
    detector = ResumeChangeDetector()

    old_profile = CandidateProfile(
        skills=SkillsSection(programming_languages=["Python", "Java"]),
        certifications=["AWS"],
        projects=[Project(name="Task Scheduler")]
    )

    new_profile = CandidateProfile(
        skills=SkillsSection(programming_languages=["Python", "Go"]),  # Java removed, Go added
        certifications=["AWS", "CKAD"],  # CKAD added
        projects=[]  # Task Scheduler removed
    )

    report = detector.detect_changes(old_profile, new_profile)

    assert "skills" in report
    assert report["skills"]["added"] == ["Go"]
    assert report["skills"]["removed"] == ["Java"]

    assert "certifications" in report
    assert report["certifications"]["added"] == ["CKAD"]
    assert report["certifications"]["removed"] == []

    assert "projects" in report
    assert report["projects"]["added"] == []
    assert report["projects"]["removed"] == ["Task Scheduler"]
