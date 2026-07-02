"""
resume_parser/cache_manager.py — JSON Profile Cache Manager
============================================================
Purpose
-------
Provide robust profile caching to avoid parsing the same resume file repeatedly.

Design Decisions
----------------
Hash-based Invalidation:
    - We calculate the SHA-256 fingerprint of the resume file.
    - If the file matches the cached hash, we return the cached profile immediately.
    - If the file is modified or replaced, the hash changes, triggering a rebuild.

Aggressive Verification:
    - When loading from cache, we validate the JSON data against the `CandidateProfile`
      Pydantic schema.
    - If the schema validation fails (due to cache corruption or code updates),
      we treat it as a cache miss, log a warning, and rebuild.

Usage
-----
    from resume_parser.cache_manager import CacheManager
    from pathlib import Path

    cache = CacheManager(cache_dir=Path("cache"))
    profile = cache.load_profile(resume_path)
    if not profile:
        # miss -> parse and build profile
        cache.save_profile(profile, resume_path)
"""

from __future__ import annotations

import json
from pathlib import Path

from resume_parser.profile_model import CandidateProfile
from resume_parser.change_detector import ResumeChangeDetector
from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Manages loading, saving, and verifying the parsed candidate profile cache.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            from config import settings
            cache_dir = settings.cache_dir
        self.cache_dir = Path(cache_dir).resolve()
        self.detector = ResumeChangeDetector()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_cached_hash(self) -> str | None:
        """
        Read the stored SHA-256 hash from cache/resume_hash.txt.

        Returns
        -------
        str | None
            The hash string, or None if the file doesn't exist.
        """
        hash_file = self.cache_dir / "resume_hash.txt"
        if hash_file.exists():
            try:
                return hash_file.read_text(encoding="utf-8").strip()
            except Exception as exc:
                logger.warning(f"Failed to read resume hash cache file: {exc}")
        return None

    def get_current_hash(self, resume_path: Path) -> str:
        """
        Calculate SHA-256 of the active resume file.

        Parameters
        ----------
        resume_path : Path
            Path to the resume file.

        Returns
        -------
        str
            The SHA-256 hex digest.
        """
        return self.detector.calculate_hash(resume_path)

    def is_cache_valid(self, resume_path: Path) -> bool:
        """
        Check if the cached profile matches the active resume file.

        Parameters
        ----------
        resume_path : Path
            Path to the resume file.

        Returns
        -------
        bool
            True if hashes match and cache files exist.
        """
        profile_file = self.cache_dir / "candidate_profile.json"
        if not profile_file.exists():
            return False

        cached_hash = self.get_cached_hash()
        if not cached_hash:
            return False

        try:
            current_hash = self.get_current_hash(resume_path)
            return cached_hash == current_hash
        except Exception as exc:
            logger.warning(f"Error checking cache validity: {exc}")
            return False

    def load_profile(self, resume_path: Path) -> CandidateProfile | None:
        """
        Load and validate the CandidateProfile from the cache.

        Parameters
        ----------
        resume_path : Path
            Path to the resume file.

        Returns
        -------
        CandidateProfile | None
            The profile object if cache is valid, else None.
        """
        if not self.is_cache_valid(resume_path):
            logger.info("Cache miss: resume hash changed or cache files do not exist.")
            return None

        profile_file = self.cache_dir / "candidate_profile.json"
        logger.info("Loading candidate profile from cache", extra={"path": str(profile_file)})

        try:
            data = json.loads(profile_file.read_text(encoding="utf-8"))
            # Validate against Pydantic schema
            profile = CandidateProfile.model_validate(data)
            logger.info(
                "Resume unchanged. Loaded profile from cache.",
                extra={"candidate_name": profile.personal.name, "roles_count": len(profile.inferred_roles)}
            )
            return profile
        except Exception as exc:
            logger.warning(
                f"Failed to validate cached profile schema. Rebuilding: {exc}",
                extra={"cache_file": str(profile_file)}
            )
            return None

    def save_profile(self, profile: CandidateProfile, resume_path: Path) -> None:
        """
        Save the CandidateProfile and its file hash to the cache directory.

        Parameters
        ----------
        profile : CandidateProfile
            The populated profile object.
        resume_path : Path
            Path to the resume file.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # 1. Save profile JSON
            profile_file = self.cache_dir / "candidate_profile.json"
            profile_json = profile.to_json(indent=2)
            profile_file.write_text(profile_json, encoding="utf-8")

            # 2. Save hash file
            hash_file = self.cache_dir / "resume_hash.txt"
            current_hash = self.get_current_hash(resume_path)
            hash_file.write_text(current_hash, encoding="utf-8")

            logger.info(
                "Candidate profile cached successfully",
                extra={
                    "profile_file": str(profile_file),
                    "hash_file": str(hash_file),
                    "hash": current_hash[:10]
                }
            )
        except Exception as exc:
            logger.error(f"Failed to save profile cache: {exc}", extra={"path": str(self.cache_dir)})
