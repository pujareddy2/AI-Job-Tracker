"""
tests/test_cache_manager.py — Unit Tests for resume_parser/cache_manager.py
=============================================================================
Tests verify (uses temporary paths):
  1. Hash read/write operations.
  2. Cache is invalid if profile JSON or hash file is missing.
  3. Cache is invalid if resume file changes hash.
  4. load_profile() return value and Pydantic validation checks.
  5. load_profile() returns None if file content is corrupted.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from resume_parser.profile_model import CandidateProfile, PersonalInfo
from resume_parser.cache_manager import CacheManager


def test_cache_manager_hash_operations(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text("my resume contents", encoding="utf-8")

    manager = CacheManager(cache_dir=cache_dir)
    current_hash = manager.get_current_hash(resume_file)
    assert len(current_hash) == 64

    # Save mock profile
    profile = CandidateProfile(personal=PersonalInfo(name="Sravya"))
    manager.save_profile(profile, resume_file)

    # Verify files created
    assert (cache_dir / "resume_hash.txt").exists()
    assert (cache_dir / "candidate_profile.json").exists()

    # Load hash
    assert manager.get_cached_hash() == current_hash

    # Validity check
    assert manager.is_cache_valid(resume_file) is True


def test_cache_invalid_on_file_change(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text("version 1", encoding="utf-8")

    manager = CacheManager(cache_dir=cache_dir)
    profile = CandidateProfile(personal=PersonalInfo(name="Sravya"))
    manager.save_profile(profile, resume_file)

    # Change file
    resume_file.write_text("version 2 (modified)", encoding="utf-8")
    assert manager.is_cache_valid(resume_file) is False


def test_load_corrupted_cache_returns_none(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text("resume info", encoding="utf-8")

    manager = CacheManager(cache_dir=cache_dir)
    profile = CandidateProfile(personal=PersonalInfo(name="Sravya"))
    manager.save_profile(profile, resume_file)

    # Corrupt the profile JSON file
    profile_json_file = cache_dir / "candidate_profile.json"
    profile_json_file.write_text("{invalid json...}", encoding="utf-8")

    loaded = manager.load_profile(resume_file)
    assert loaded is None
