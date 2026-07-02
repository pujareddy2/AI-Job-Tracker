"""
resume_parser/detector.py — Resume File Detector
=================================================
Purpose
-------
Automatically locate the newest resume file in the configured resume directory.

Design Decisions
----------------
Why auto-detection instead of a config variable?
    - Users frequently rename resumes (e.g. "Resume_v2.pdf", "Sravya_June2026.pdf").
    - Hardcoding filenames is a maintenance burden and a common source of bugs.
    - By always picking the newest file, the system self-updates when the user
      drops in a new resume — no config change needed.

Why sort by mtime (modification time)?
    - mtime reflects when the file was last changed, not when it was created.
    - This handles the common case of a user editing and re-saving the same file.
    - It works correctly even if the user copies from another location (the copy
      gets a new mtime in most OS environments).

Supported extensions: .pdf, .docx, .txt
    - PDF: most common resume format, highest fidelity.
    - DOCX: Word format, widely used in enterprise hiring.
    - TXT: plain text, useful for testing and simple resumes.

Usage
-----
    from resume_parser.detector import ResumeDetector
    from pathlib import Path

    detector = ResumeDetector(resume_dir=Path("resume"))
    path = detector.find_newest()
    print(path)  # -> PosixPath('resume/Sravya_Resume_2026.pdf')
"""

from __future__ import annotations

from pathlib import Path

from utils.exceptions import ResumeParserError
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})


class ResumeDetector:
    """
    Scans a directory and returns the newest resume file.

    Parameters
    ----------
    resume_dir : Path
        Directory to scan.  Defaults to the ``resume/`` folder at project root.
        Created automatically if it does not exist.

    Attributes
    ----------
    resume_dir : Path
        The resolved, absolute resume directory path.
    """

    def __init__(self, resume_dir: Path | None = None) -> None:
        if resume_dir is None:
            from config import settings
            resume_dir = settings.resume_dir
        self.resume_dir = Path(resume_dir).resolve()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def find_newest(self) -> Path:
        """
        Find and return the newest resume file in ``resume_dir``.

        The newest file is determined by ``stat().st_mtime`` (modification time).

        Returns
        -------
        Path
            Absolute path to the newest resume file.

        Raises
        ------
        ResumeParserError
            If ``resume_dir`` does not exist, is empty, or contains no supported
            resume files.
        """
        self._ensure_dir_exists()

        candidates = self._collect_candidates()

        if not candidates:
            raise ResumeParserError(
                f"No resume files found in '{self.resume_dir}'. "
                f"Supported formats: {sorted(SUPPORTED_EXTENSIONS)}. "
                "Drop your resume (PDF, DOCX, or TXT) into the 'resume/' directory.",
                resume_dir=str(self.resume_dir),
            )

        # Sort by modification time descending; pick the first (newest).
        newest = max(candidates, key=lambda p: p.stat().st_mtime)

        logger.info(
            "Resume detected",
            extra={
                "path": str(newest),
                "extension": newest.suffix,
                "candidates_found": len(candidates),
            },
        )
        return newest

    def list_all(self) -> list[Path]:
        """
        Return all supported resume files in the directory, sorted newest-first.

        Useful for displaying a list to the user or for testing.

        Returns
        -------
        list[Path]
            All resume paths, sorted by mtime descending (newest first).
        """
        self._ensure_dir_exists()
        candidates = self._collect_candidates()
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

    def has_resume(self) -> bool:
        """
        Return True if at least one supported resume file exists.

        Returns
        -------
        bool
        """
        try:
            self._ensure_dir_exists()
            return bool(self._collect_candidates())
        except ResumeParserError:
            return False

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _ensure_dir_exists(self) -> None:
        """
        Create the resume directory if it does not exist.

        This prevents a confusing FileNotFoundError when the directory has
        never been used.  The directory is created silently.

        Raises
        ------
        ResumeParserError
            If the path exists but is a file, not a directory.
        """
        if self.resume_dir.exists() and not self.resume_dir.is_dir():
            raise ResumeParserError(
                f"'{self.resume_dir}' exists but is a file, not a directory.",
                resume_dir=str(self.resume_dir),
            )
        self.resume_dir.mkdir(parents=True, exist_ok=True)

    def _collect_candidates(self) -> list[Path]:
        """
        Collect all supported resume files from the directory (non-recursive).

        Non-recursive by design: the resume directory should be flat.
        Hidden files (starting with '.') are excluded.

        Returns
        -------
        list[Path]
            Files with a supported extension, excluding hidden files.
        """
        candidates: list[Path] = []
        for path in self.resume_dir.iterdir():
            if path.is_file() and not path.name.startswith("."):
                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    candidates.append(path)
        return candidates
