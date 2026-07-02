"""
application_assistant/config.py — Configuration settings for Job Assistant
==========================================================================
Purpose
-------
Configuration options, directories, intervals, and templates for job application assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from config import PROJECT_ROOT


@dataclass
class AssistantConfig:
    """Configuration settings for Application Monitor and State Machine."""
    resume_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "resume")
    monitoring_interval: int = 5  # seconds
    states_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "cache" / "application_states")
    versions_file: Path = field(default_factory=lambda: PROJECT_ROOT / "cache" / "resume_versions.json")
    manual_apps_path: Path = field(default_factory=lambda: PROJECT_ROOT / "cache" / "manual_applications.json")
    require_user_approval: bool = True

    # Required form fields to audit for missing information detection
    required_form_fields: list[str] = field(default_factory=lambda: [
        "name", "email", "phone", "linkedin", "github", "resume",
        "expected_salary", "notice_period", "work_authorization"
    ])


# Default configuration instance
DEFAULT_ASSISTANT_CONFIG = AssistantConfig()
