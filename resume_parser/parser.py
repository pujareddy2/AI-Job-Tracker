"""
resume_parser/parser.py — Resume Parser Interface
==================================================
Purpose
-------
Provide a backward-compatible class interface for parsing a specific resume file.

This module re-exports or wraps the full ProfileBuilder and CandidateProfile
orchestrators under the legacy `ResumeParser` class name.

Usage
-----
    from resume_parser.parser import ResumeParser
    from pathlib import Path

    parser = ResumeParser(resume_path=Path("resume/my_resume.pdf"))
    profile_dict = parser.parse()
    print(profile_dict["personal"]["name"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from resume_parser.profile_builder import ProfileBuilder
from utils.exceptions import ResumeParserError
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeParser:
    """
    Extracts structured data from a specific resume file.

    Parameters
    ----------
    resume_path : Path
        Path to the PDF, DOCX, or TXT resume file.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})

    def __init__(self, resume_path: Path) -> None:
        self.resume_path = Path(resume_path).resolve()

    def parse(self) -> dict[str, Any]:
        """
        Parse the resume and return a structured dictionary.

        Returns
        -------
        dict[str, Any]
            The CandidateProfile serialised as a dictionary.

        Raises
        ------
        ResumeParserError
            If the file does not exist or has an unsupported extension.
        """
        if not self.resume_path.exists():
            raise ResumeParserError(
                f"Resume file not found: {self.resume_path}",
                path=str(self.resume_path),
            )

        ext = self.resume_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ResumeParserError(
                f"Unsupported file type: {ext!r}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}",
                path=str(self.resume_path),
            )

        logger.info(
            "Parsing resume file via ResumeParser",
            extra={"path": str(self.resume_path)},
        )

        # Instantiate ProfileBuilder targeting the specific resume's directory
        builder = ProfileBuilder(
            resume_dir=self.resume_path.parent
        )

        # Force rebuild to ensure we parse the *specific* requested file path
        # rather than whatever is newest in the directory cache.
        profile = builder.build(force_rebuild=True)

        return profile.model_dump(mode="json")
