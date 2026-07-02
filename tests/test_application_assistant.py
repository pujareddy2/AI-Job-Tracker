"""
tests/test_application_assistant.py — State Machine & Version Intelligence Tests
=================================================================================
Purpose
-------
Verify dynamic resume intelligence, automatic pre-filling, custom input resolution,
and user approval safety rules.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
import pytest

from application_assistant.config import AssistantConfig
from application_assistant.engine import ApplicationAssistantEngine
from application_assistant.models import ApplicationState
from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
from application_assistant.resume_monitor import ResumeMonitor


@pytest.fixture
def temp_config(tmp_path) -> AssistantConfig:
    """Creates a temporary config directing to isolated folders."""
    resume_dir = tmp_path / "resume"
    resume_dir.mkdir()
    
    # Create mock resumes
    (resume_dir / "Puja_General_Resume.pdf").write_text("Mock PDF Content 1")
    (resume_dir / "Puja_AI_Resume.pdf").write_text("Mock PDF Content 2")

    return AssistantConfig(
        resume_dir=resume_dir,
        states_dir=tmp_path / "application_states",
        versions_file=tmp_path / "resume_versions.json",
        manual_apps_path=tmp_path / "manual_applications.json"
    )


@pytest.fixture
def mock_profile() -> dict:
    return {
        "meta": {
            "resume_filename": "Puja_General_Resume.pdf"
        },
        "personal": {
            "name": "PUJA MIDDE",
            "email": "middepuja1005@gmail.com",
            "phone": "9121290915",
            "linkedin": "linkedin.com/in/puja-midde3",
            "github": "github.com/pujareddy2",
            "portfolio": "https://pujareddy.me",
            "location": "Hyderabad"
        },
        "education": {
            "degree": "B.Tech",
            "branch": "Computer Science",
            "institution": "Stanley College",
            "cgpa": "8.6/10"
        },
        "skills": {
            "programming_languages": ["Python"]
        },
        "projects": [],
        "experience": {"level": "Fresher", "internships": []}
    }


def test_resume_monitor_version_tracking(temp_config):
    """Verify that monitor registers additions, deletions, and updates correctly."""
    mon = ResumeMonitor(temp_config)
    changes = mon.scan_directory()

    # Both resumes registered as new
    assert len(changes) == 2
    assert "New" in changes.values()

    # Inactive by default; one set to active automatically
    versions = mon.load_versions()
    assert any(v.is_active for v in versions.values())

    # Switch active
    inactive_hash = [k for k, v in versions.items() if not v.is_active][0]
    assert mon.set_active_resume(inactive_hash)
    assert mon.get_active_resume().file_hash == inactive_hash


def test_prefill_and_missing_field_detection(temp_config, mock_profile):
    """Verify prefiller maps profile fields and flags missing checklist items."""
    orch = ApplicationWorkflowOrchestrator(temp_config)
    job = {
        "identity": {"uuid": "job-test-123"},
        "job": {"job_title": "AI Developer"},
        "company": {"company_name": "OpenAI"}
    }

    # Start application
    state = orch.start_application(mock_profile, job, "Puja_AI_Resume.pdf")

    # Missing notice_period, expected_salary, and work_authorization
    assert state.state == "Waiting for Information"
    assert "expected_salary" in state.missing_fields
    assert "notice_period" in state.missing_fields
    assert "work_authorization" in state.missing_fields
    assert state.filled_fields["name"] == "PUJA MIDDE"
    assert state.readiness_score < 100
    assert state.readiness_label == "Needs Information"
    assert any("missing details" in action.lower() for action in state.recommended_actions)


def test_missing_info_resolution_and_user_approval(temp_config, mock_profile):
    """Verify state flow: Waiting for Info -> Waiting for Approval -> Submitted."""
    orch = ApplicationWorkflowOrchestrator(temp_config)
    job = {
        "identity": {"uuid": "job-test-123"},
        "job": {"job_title": "AI Developer"},
        "company": {"company_name": "OpenAI"}
    }

    state = orch.start_application(mock_profile, job, "Puja_AI_Resume.pdf")
    assert state.state == "Waiting for Information"

    # Provide custom inputs resolving gaps
    custom_inputs = {
        "expected_salary": "8,00,000 INR",
        "notice_period": "Immediate",
        "work_authorization": "Yes"
    }
    state = orch.provide_missing_information("job-test-123", mock_profile, custom_inputs)

    assert state.state == "Waiting for Approval"
    assert len(state.missing_fields) == 0

    # User grants approval
    state = orch.approve_application("job-test-123")
    assert state.state == "Submitted"
    assert state.history[-1].to_state == "Submitted"


def test_orchestration_callbacks(temp_config):
    """Verify that monitor triggers matching engine callbacks on file change."""
    engine = ApplicationAssistantEngine(temp_config)
    
    # Initialize monitor cache first
    engine.monitor.scan_directory()

    called_profile = False
    called_match = False

    def mock_profile_builder():
        nonlocal called_profile
        called_profile = True

    def mock_matching_engine():
        nonlocal called_match
        called_match = True

    # No changes first scan after initialization
    changes1 = engine.scan_and_sync_resumes(mock_profile_builder, mock_matching_engine)
    assert not called_profile

    # Add a new file to trigger scan change
    (temp_config.resume_dir / "Puja_ML_Resume.pdf").write_text("ML Resume Content")
    changes2 = engine.scan_and_sync_resumes(mock_profile_builder, mock_matching_engine)

    assert "New" in changes2.values()
    assert called_profile
    assert called_match
