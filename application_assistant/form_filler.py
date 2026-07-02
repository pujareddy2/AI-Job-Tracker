"""
application_assistant/form_filler.py — Application Form Prefiller
===================================================================
Purpose
-------
Matches required fields against CandidateProfile and extracts prefilled
values. Identifies missing fields for user confirmation.
"""

from __future__ import annotations

from typing import Any
from application_assistant.config import DEFAULT_ASSISTANT_CONFIG, AssistantConfig


class ApplicationFormFiller:
    """Matches form input definitions with candidate profile metrics."""

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or DEFAULT_ASSISTANT_CONFIG

    def prefill_form(
        self,
        profile: dict[str, Any],
        custom_inputs: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], list[str]]:
        """
        Prefill known fields from profile and identify missing items.

        Parameters
        ----------
        profile : dict
            CandidateProfile dictionary.
        custom_inputs : dict, optional
            Manually provided user values to override/fill missing fields.

        Returns
        -------
        filled : dict[str, str]
            Map of field names to values.
        missing : list[str]
            List of required fields that are empty.
        """
        personal = profile.get("personal", {})
        edu = profile.get("education", {})
        custom = custom_inputs or {}

        # 1. Gather all profile facts
        profile_facts = {
            "name": personal.get("name", "").strip(),
            "email": personal.get("email", "").strip(),
            "phone": personal.get("phone", "").strip(),
            "linkedin": personal.get("linkedin", "").strip(),
            "github": personal.get("github", "").strip(),
            "portfolio": personal.get("portfolio", "").strip(),
            "address": personal.get("location", "").strip(),
            "resume": profile.get("meta", {}).get("resume_filename", "").strip(),
            "expected_salary": "",
            "notice_period": "",
            "work_authorization": ""
        }

        # 2. Merge manually provided custom inputs
        for k, v in custom.items():
            profile_facts[k] = v

        # 3. Separate filled and missing required fields
        filled = {}
        missing = []

        for field_name in self.config.required_form_fields:
            val = profile_facts.get(field_name, "").strip()
            if val:
                filled[field_name] = val
            else:
                missing.append(field_name)

        return filled, missing

    def audit_application_readiness(
        self,
        profile: dict[str, Any],
        custom_inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Audit both required fields and document checklist to calculate a comprehensive
        readiness score and identify missing items.
        """
        personal = profile.get("personal", {})
        custom = custom_inputs or {}

        # 1. Required Fields Check
        required_fields = ["name", "email", "phone", "expected_salary", "notice_period", "work_authorization"]
        filled_fields = {}
        missing_fields = []

        field_sources = {
            "name": personal.get("name", "").strip(),
            "email": personal.get("email", "").strip(),
            "phone": personal.get("phone", "").strip(),
            "expected_salary": custom.get("expected_salary", "").strip(),
            "notice_period": custom.get("notice_period", "").strip(),
            "work_authorization": custom.get("work_authorization", "").strip() or personal.get("work_authorization", "").strip()
        }

        for f in required_fields:
            val = field_sources.get(f)
            if val:
                filled_fields[f] = val
            else:
                missing_fields.append(f)

        # 2. Required Documents Check
        required_docs = ["Resume", "Cover Letter", "Portfolio", "GitHub", "LinkedIn", "Certificates", "Passport", "Visa", "Photo"]
        missing_docs = []

        # Check presence of documents
        has_resume = bool(profile.get("meta", {}).get("resume_filename", "").strip() or custom.get("Resume"))
        has_portfolio = bool(personal.get("portfolio", "").strip() or custom.get("Portfolio"))
        has_github = bool(personal.get("github", "").strip() or custom.get("GitHub"))
        has_linkedin = bool(personal.get("linkedin", "").strip() or custom.get("LinkedIn"))
        has_certificates = bool(profile.get("certifications") or custom.get("Certificates"))
        
        # Passport, Visa, Photo, Cover Letter are usually provided via custom inputs
        has_cover_letter = bool(custom.get("Cover Letter")) or bool(custom.get("cover_letter"))
        has_passport = bool(custom.get("Passport")) or bool(custom.get("passport"))
        has_visa = bool(custom.get("Visa")) or bool(custom.get("visa"))
        has_photo = bool(custom.get("Photo")) or bool(custom.get("photo"))

        doc_presence = {
            "Resume": has_resume,
            "Cover Letter": has_cover_letter,
            "Portfolio": has_portfolio,
            "GitHub": has_github,
            "LinkedIn": has_linkedin,
            "Certificates": has_certificates,
            "Passport": has_passport,
            "Visa": has_visa,
            "Photo": has_photo
        }

        for doc in required_docs:
            if not doc_presence[doc]:
                missing_docs.append(doc)

        # 3. Calculate Score
        total_items = len(required_fields) + len(required_docs)
        filled_items = (len(required_fields) - len(missing_fields)) + (len(required_docs) - len(missing_docs))
        score = (filled_items / total_items) * 100.0

        return {
            "readiness_score": round(score, 2),
            "filled_fields": filled_fields,
            "missing_fields": missing_fields,
            "required_documents": required_docs,
            "missing_documents": missing_docs
        }
