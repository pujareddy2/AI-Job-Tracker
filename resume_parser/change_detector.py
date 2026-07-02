"""
resume_parser/change_detector.py — Resume Change Detector
==========================================================
Purpose
-------
Compare two versions of a candidate profile and detect additions, removals,
and changes in skills, internships, certifications, and projects.

Design Decisions
----------------
Hash Check vs Semantic Check:
    - We first compare SHA-256 hashes of the files (handled by the CacheManager).
    - If the hashes mismatch, we run the parser and compare the resulting Pydantic
      models field-by-field.
    - This generates a precise change report logging exactly what skills, projects,
      or certifications were added or removed.

Structured Diff Output:
    - The change report is returned as a nested dictionary, which is saved on the
      profile's `change_report` field and logged for deployment visibility.

Usage
-----
    from resume_parser.change_detector import ResumeChangeDetector
    from resume_parser.profile_model import CandidateProfile

    detector = ResumeChangeDetector()
    report = detector.detect_changes(old_profile, new_profile)
    # -> {"skills": {"added": ["LangChain"], "removed": []}, ...}
"""

from __future__ import annotations

import hashlib
from typing import Any

from resume_parser.profile_model import CandidateProfile
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeChangeDetector:
    """
    Compares two CandidateProfile objects to detect differences.
    """

    def calculate_hash(self, file_path: str | Path) -> str:
        """
        Calculate the SHA-256 hash of a file's content.

        Parameters
        ----------
        file_path : str | Path
            The file to hash.

        Returns
        -------
        str
            The SHA-256 hex digest.
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def detect_changes(
        self,
        old_profile: CandidateProfile | None,
        new_profile: CandidateProfile
    ) -> dict[str, Any]:
        """
        Compare old and new profiles and return a detailed change report.

        Parameters
        ----------
        old_profile : CandidateProfile, optional
            The previous CandidateProfile loaded from cache.
        new_profile : CandidateProfile
            The newly parsed CandidateProfile.

        Returns
        -------
        dict[str, Any]
            The change report. Empty if old_profile is None or no changes.
        """
        if not old_profile:
            logger.info("No previous profile found. Skipping change detection.")
            return {}

        logger.info("Detecting changes between resume versions")

        # 1. Compare Skills
        old_skills = set(old_profile.skills.all_skills())
        new_skills = set(new_profile.skills.all_skills())

        added_skills = sorted(list(new_skills - old_skills))
        removed_skills = sorted(list(old_skills - new_skills))

        # 2. Compare Certifications
        old_certs = set(old_profile.certifications)
        new_certs = set(new_profile.certifications)

        added_certs = sorted(list(new_certs - old_certs))
        removed_certs = sorted(list(old_certs - new_certs))

        # 3. Compare Projects
        old_projs = {p.name.lower() for p in old_profile.projects if p.name}
        new_projs = {p.name.lower() for p in new_profile.projects if p.name}

        added_projs = []
        for p in new_profile.projects:
            if p.name and p.name.lower() not in old_projs:
                added_projs.append(p.name)

        removed_projs = []
        for p in old_profile.projects:
            if p.name and p.name.lower() not in new_projs:
                removed_projs.append(p.name)

        # 4. Compare Internships
        old_interns = {i.company.lower() for i in old_profile.experience.internships if i.company}
        new_interns = {i.company.lower() for i in new_profile.experience.internships if i.company}

        added_interns = []
        for i in new_profile.experience.internships:
            if i.company and i.company.lower() not in old_interns:
                added_interns.append(f"{i.role} at {i.company}")

        removed_interns = []
        for i in old_profile.experience.internships:
            if i.company and i.company.lower() not in new_interns:
                removed_interns.append(f"{i.role} at {i.company}")

        report: dict[str, Any] = {}

        # Only add keys to report if there is an actual difference
        if added_skills or removed_skills:
            report["skills"] = {"added": added_skills, "removed": removed_skills}
        if added_certs or removed_certs:
            report["certifications"] = {"added": added_certs, "removed": removed_certs}
        if added_projs or removed_projs:
            report["projects"] = {"added": added_projs, "removed": removed_projs}
        if added_interns or removed_interns:
            report["internships"] = {"added": added_interns, "removed": removed_interns}

        if report:
            logger.info(
                "Resume changes detected",
                extra={
                    "skills_added": len(added_skills),
                    "skills_removed": len(removed_skills),
                    "projects_added": len(added_projs),
                    "internships_added": len(added_interns)
                }
            )
        else:
            logger.info("No semantic changes detected between resume versions")

        return report
