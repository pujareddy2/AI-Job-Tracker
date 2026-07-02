"""
tests/test_notifications.py
===========================
Tests the Notification engine and Jinja2 HTML report generator.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest

from notifications.email_notifier import EmailNotifier
from notifications.report_generator import ReportGenerator
from job_model.universal_model import (
    UniversalJobModel,
    IdentityModel,
    CompanyModel,
    JobInfoModel,
    LocationModel,
    AIClassificationModel,
    ResumeMatchModel,
    ApplicationModel,
    InternshipModel,
    ReliabilityModel,
    MetadataModel,
)


@pytest.fixture
def sample_jobs() -> list[UniversalJobModel]:
    return [
        UniversalJobModel(
            identity=IdentityModel(job_id="test1", uuid="u1"),
            company=CompanyModel(company_name="Tech Corp"),
            job=JobInfoModel(job_title="Software Engineer"),
            location=LocationModel(location="Remote"),
            ai_classification=AIClassificationModel(),
            resume_match=ResumeMatchModel(candidate_match_score=95, resume_keywords_missing=["AWS", "Docker"]),
            application=ApplicationModel(application_url="http://apply", platform="LinkedIn"),
            internship=InternshipModel(is_internship=False),
            reliability=ReliabilityModel(reliability_score=90),
            metadata=MetadataModel(discovered_date="2026-06-28T00:00:00Z", timestamp="2026-06-28T00:00:00Z")
        ),
        UniversalJobModel(
            identity=IdentityModel(job_id="test2", uuid="u2"),
            company=CompanyModel(company_name="Startup Inc"),
            job=JobInfoModel(job_title="Data Scientist Intern"),
            location=LocationModel(location="Onsite"),
            ai_classification=AIClassificationModel(),
            resume_match=ResumeMatchModel(candidate_match_score=85, resume_keywords_missing=["Docker"]),
            application=ApplicationModel(application_url="http://apply", platform="Indeed"),
            internship=InternshipModel(is_internship=True, ppo_available=True),
            reliability=ReliabilityModel(reliability_score=80),
            metadata=MetadataModel(discovered_date="2026-06-28T00:00:00Z", timestamp="2026-06-28T00:00:00Z")
        )
    ]


def test_report_generator_html(sample_jobs: list[UniversalJobModel]):
    """Test if HTML report is successfully generated from jobs."""
    generator = ReportGenerator()
    html = generator.generate_html_report(sample_jobs)
    
    assert "AI Career Assistant" in html
    assert "Tech Corp" in html
    assert "Startup Inc" in html
    assert "PPO Available" in html
    assert "Skills Gap Analysis" in html
    assert "Docker" in html
    assert "Recommended Actions" in html


@patch("smtplib.SMTP")
def test_email_notifier_send(mock_smtp, sample_jobs: list[UniversalJobModel]):
    """Test successful email dispatch when conditions are met."""
    with patch("notifications.email_notifier.settings") as mock_settings:
        mock_settings.email_address = "test@example.com"
        mock_settings.email_password = "password"
        
        notifier = EmailNotifier()
        result = notifier.send_report(sample_jobs)
        
        assert result is True
        mock_smtp.assert_called_once()


@patch("smtplib.SMTP")
def test_email_notifier_sends_empty_report(mock_smtp):
    """Test that empty jobs still send a completion email."""
    with patch("notifications.email_notifier.settings") as mock_settings:
        mock_settings.email_address = "test@example.com"
        mock_settings.email_password = "password"

        notifier = EmailNotifier()
        result = notifier.send_report([])

        assert result is True
        mock_smtp.assert_called_once()


@patch("smtplib.SMTP")
def test_email_notifier_skip_duplicates(mock_smtp, sample_jobs: list[UniversalJobModel]):
    """Test that duplicate-only reports still send an empty-results email."""
    for job in sample_jobs:
        job.reliability.duplicate = True

    with patch("notifications.email_notifier.settings") as mock_settings:
        mock_settings.email_address = "test@example.com"
        mock_settings.email_password = "password"

        notifier = EmailNotifier()
        result = notifier.send_report(sample_jobs)

        assert result is True
        mock_smtp.assert_called_once()
