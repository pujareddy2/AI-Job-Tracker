"""
tests/test_job_serializers.py — Unit Tests for JobSerializer Adapters
=====================================================================
"""

from __future__ import annotations

from job_model.validator import JobValidator
from job_model.serializers import JobSerializer


def test_serializer_outputs() -> None:
    validator = JobValidator()
    raw = {
        "company": "OpenAI",
        "role": "LLM Engineer",
        "location": "San Francisco, USA",
        "application_url": "https://openai.com/jobs/llm-engineer-0",
        "platform": "LinkedIn",
        "source_reliability_score": 98,
        "posting_date": "2026-06-28",
        "job_description": "We are seeking a developer with FastAPI and LangChain."
    }

    norm = validator.normalize(raw)

    # 1. SQLite Flat Dictionary Serialisation
    sql_dict = JobSerializer.to_sqlite_dict(norm)
    assert sql_dict["company_name"] == "OpenAI"
    assert sql_dict["job_title"] == "LLM Engineer"
    assert sql_dict["country"] == "United States"
    assert sql_dict["platform"] == "LinkedIn"
    assert sql_dict["remote"] == 0  # converted to int for DB boolean storage

    # 2. Google Sheets List Row Mappings
    row = JobSerializer.to_sheets_row(norm)
    assert len(row) == 10
    assert row[2] == "OpenAI"  # Company
    assert row[3] == "LLM Engineer"  # Role
    assert row[8] == "https://openai.com/jobs/llm-engineer-0"  # URL

    # 3. CSV Conversion Mappings
    csv_str = JobSerializer.to_csv([norm])
    assert "company_name" in csv_str
    assert "OpenAI" in csv_str
    assert "LLM Engineer" in csv_str
