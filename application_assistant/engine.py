"""
application_assistant/engine.py — Master orchestrator for Job Assistant
========================================================================
Purpose
-------
Integrates the ResumeMonitor and ApplicationWorkflowOrchestrator to monitor
directories, prefill applications, detect gaps, and request user actions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application_assistant.config import DEFAULT_ASSISTANT_CONFIG, AssistantConfig
from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
from application_assistant.resume_monitor import ResumeMonitor
from utils.logger import get_logger

logger = get_logger("application_assistant_engine")


class ApplicationAssistantEngine:
    """Entry point for dynamic resume monitoring and autonomous form prefilling."""

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or DEFAULT_ASSISTANT_CONFIG
        self.monitor = ResumeMonitor(self.config)
        self.orchestrator = ApplicationWorkflowOrchestrator(self.config)

    def scan_and_sync_resumes(
        self,
        profile_builder_fn: Any,
        matching_engine_fn: Any,
    ) -> dict[str, str]:
        """
        Scan the resume directory for changes and trigger down-stream updates
        if any addition, modification, or rename occurs.
        """
        changes = self.monitor.scan_directory()
        modified = any(status in ("New", "Updated", "Renamed", "Deleted") for status in changes.values())

        if modified:
            logger.info("Resume modifications detected. Invoking orchestrator callbacks...")
            self.orchestrator.handle_resume_change(profile_builder_fn, matching_engine_fn)
        else:
            logger.debug("No resume directory updates found.")

        return changes

    def prepare_job_applications(
        self,
        profile: dict[str, Any],
        jobs: list[dict[str, Any]],
    ) -> list[Any]:
        """
        Initiate or resume application prep workflows for the given list of jobs.
        """
        active_resume = self.monitor.get_active_resume()
        resume_name = active_resume.filename if active_resume else "None"

        states = []
        for job in jobs[:10]:  # Limit to top 10 matched jobs per check
            try:
                state = self.orchestrator.start_application(profile, job, resume_name)
                states.append(state)
            except Exception as exc:
                logger.error(f"Failed to prepare application for job {job.get('identity', {}).get('uuid', 'unknown')}: {exc}")

        return states
