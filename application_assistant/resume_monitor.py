"""
application_assistant/resume_monitor.py — Dynamic Resume Intelligence Monitor
=============================================================================
Purpose
-------
Monitors the resume directory, tracks version hashes, and handles transitions.
Selects the best resume version for any job listing based on keyword matching.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from application_assistant.config import DEFAULT_ASSISTANT_CONFIG, AssistantConfig
from application_assistant.models import ResumeVersion
from utils.logger import get_logger

logger = get_logger("resume_monitor")


def _compute_hash(path: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class ResumeMonitor:
    """Watches the resume directory and logs file version updates."""

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or DEFAULT_ASSISTANT_CONFIG
        self.resume_dir = self.config.resume_dir
        self.versions_file = self.config.versions_file

    def load_versions(self) -> dict[str, ResumeVersion]:
        """Load registered resume versions from cache."""
        if not self.versions_file.exists():
            return {}
        try:
            data = json.loads(self.versions_file.read_text(encoding="utf-8"))
            return {k: ResumeVersion.model_validate(v) for k, v in data.items()}
        except Exception as exc:
            logger.warning(f"Failed to load resume versions: {exc}")
            return {}

    def save_versions(self, versions: dict[str, ResumeVersion]) -> None:
        """Save resume versions to cache."""
        self.versions_file.parent.mkdir(parents=True, exist_ok=True)
        serialized = {k: v.model_dump() for k, v in versions.items()}
        self.versions_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def scan_directory(self) -> dict[str, str]:
        """
        Scan directory and return a dict mapping hash to file change status:
        'New' | 'Updated' | 'Deleted' | 'Renamed' | 'Unchanged'
        """
        self.resume_dir.mkdir(parents=True, exist_ok=True)
        versions = self.load_versions()
        current_files = list(self.resume_dir.iterdir())
        current_files = [f for f in current_files if f.suffix.lower() in (".pdf", ".docx", ".doc")]

        scanned_hashes = {}
        changes = {}

        # Scan active files
        for f in current_files:
            file_hash = _compute_hash(f)
            scanned_hashes[file_hash] = f.name
            mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()

            # Check if hash is already known
            if file_hash in versions:
                v = versions[file_hash]
                if v.filename != f.name:
                    # Renamed
                    changes[file_hash] = "Renamed"
                    v.filename = f.name
                    v.modified_at = mtime
                else:
                    changes[file_hash] = "Unchanged"
            else:
                # New file
                changes[file_hash] = "New"
                versions[file_hash] = ResumeVersion(
                    filename=f.name,
                    created_at=datetime.now().isoformat(),
                    modified_at=mtime,
                    file_hash=file_hash,
                    is_active=False,
                    description=f"Auto-detected version: {f.name}"
                )

        # Detect deleted files
        for file_hash, v in list(versions.items()):
            if file_hash not in scanned_hashes:
                changes[file_hash] = "Deleted"
                versions.pop(file_hash)

        # Set default active resume if none is active
        if versions and not any(v.is_active for v in versions.values()):
            # Pick the newest by modification date
            newest = max(versions.values(), key=lambda v: v.modified_at)
            newest.is_active = True
            logger.info(f"Set default active resume to: {newest.filename}")

        self.save_versions(versions)
        return changes

    def get_active_resume(self) -> ResumeVersion | None:
        """Get the active resume metadata."""
        versions = self.load_versions()
        for v in versions.values():
            if v.is_active:
                return v
        if versions:
            return list(versions.values())[0]
        return None

    def set_active_resume(self, file_hash: str) -> bool:
        """Switch the default active resume version."""
        versions = self.load_versions()
        if file_hash not in versions:
            return False
        for k, v in versions.items():
            v.is_active = (k == file_hash)
        self.save_versions(versions)
        logger.info(f"Switched active resume version to: {versions[file_hash].filename}")
        return True

    def recommend_resume_version(self, job: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend the best resume version based on job title and description.
        """
        versions = self.load_versions()
        if not versions:
            return {
                "recommended_version": "None",
                "reason": "No resume versions detected in directory.",
                "improvement": 0
            }

        active = self.get_active_resume()
        title_lower = job.get("job", {}).get("job_title", "").lower()
        desc_lower = job.get("job", {}).get("job_description", "").lower()

        # Simple semantic recommendation matching
        best = active
        reason = "Only one resume version available. Utilizing by default."
        improvement = 0

        if len(versions) > 1:
            # Score each version by filename prefix relevance
            for v in versions.values():
                fname = v.filename.lower()
                if "ai" in title_lower and "ai" in fname:
                    best = v
                    reason = f"Recommended version '{v.filename}' contains matching AI keywords."
                    improvement = 10
                    break
                elif "backend" in title_lower and "backend" in fname:
                    best = v
                    reason = f"Recommended version '{v.filename}' matches Backend developer requirements."
                    improvement = 8
                    break

        return {
            "recommended_version": best.filename if best else "None",
            "reason": reason,
            "improvement": improvement
        }
