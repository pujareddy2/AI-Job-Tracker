"""
tests/test_dashboard.py — Automated Backend and Metrics Integration Tests
========================================================================
Purpose
-------
Verify FastAPI endpoints, metrics calculation engine, and manual status overrides.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from config import settings
from dashboard_backend.main import app, MANUAL_APPS_PATH
from dashboard_backend.metrics import CareerMetricsEngine


@pytest.fixture
def client() -> TestClient:
    """FastAPI Test Client."""
    return TestClient(app)


@pytest.fixture
def mock_candidate_profile() -> dict:
    return {
        "personal": {"name": "PUJA MIDDE"},
        "education": {
            "degree": "B.Tech",
            "branch": "Computer Science",
            "institution": "Stanley College",
            "cgpa": "8.6/10"
        },
        "skills": {
            "programming_languages": ["Python", "SQL"],
            "frameworks": ["FastAPI"]
        },
        "projects": [
            {"name": "LegalGuardianAI", "technologies": ["FastAPI"]}
        ],
        "experience": {"level": "Fresher", "internships": []}
    }


def test_metrics_engine_calculations(mock_candidate_profile):
    """Verify CareerMetricsEngine handles varying match and applied scopes accurately."""
    jobs = [
        {"identity": {"uuid": "job1"}, "resume_match": {"candidate_match_score": 85}},
        {"identity": {"uuid": "job2"}, "resume_match": {"candidate_match_score": 70}}
    ]
    manual_apps = {"job1": "Applied", "job2": "Saved"}
    summary = {"average_ats_score": 78.0, "gap_analysis": {}}

    res = CareerMetricsEngine.calculate_all_metrics(
        mock_candidate_profile, jobs, manual_apps, summary
    )

    assert res["career_health_score"] > 0.0
    assert res["resume_health"] == 78.0
    assert res["market_readiness"] in ("Highly Prepared", "Prepared", "Needs Improvement")


def test_api_dashboard_stats(client):
    """Verify endpoint /api/dashboard/stats returns successfully."""
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "candidate_name" in data
    assert "overall_score" in data
    assert "metrics" in data


def test_api_jobs_pagination(client):
    """Verify filter, search, and pagination on /api/jobs."""
    response = client.get("/api/jobs?page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "jobs" in data
    assert len(data["jobs"]) <= 5


def test_api_status_update_persistence(client):
    """Verify updates to status persist locally in manual_applications.json."""
    # Ensure clean state
    if MANUAL_APPS_PATH.exists():
        MANUAL_APPS_PATH.unlink()

    payload = {"job_uuid": "test-job-uuid-999", "status": "Interview"}
    response = client.post("/api/applications/status", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify write to manual_applications.json occurred
    assert MANUAL_APPS_PATH.exists()
    saved_data = json.loads(MANUAL_APPS_PATH.read_text(encoding="utf-8"))
    assert saved_data["test-job-uuid-999"] == "Interview"

    # Clean up test output
    if MANUAL_APPS_PATH.exists():
        MANUAL_APPS_PATH.unlink()
