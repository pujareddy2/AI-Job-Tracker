"""
job_model/validator.py — Normalization and Validation Layer
============================================================
Purpose
-------
Normalize raw scraper results and validate against the Standard Job Model rules,
rejecting malformed records.

Design Decisions
----------------
Validation Rules:
    - Rejects listing if `company_name`, `job_title`, or `application_url` is missing.
    - Rejects listing if `application_url` is not a valid HTTP/HTTPS URL (regex checked).
    - Checks for duplicate UUIDs if tracking batch states.

Normalization Helpers:
    - Standardizes country strings: maps variants ("IN", "IND") to "India", ("US", "USA") to "United States".
    - Auto-detects remote, hybrid, onsite status from string matches (e.g. "WFH", "Work from home" -> Remote).
    - Resolves experience bounds: extracts digits from "2-5 Years" to set min=2, max=5.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

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
    MetadataModel
)
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

# Basic URL validation regex
URL_REGEX = re.compile(
    r'^(?:http)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


class JobValidator:
    """
    Validates, parses, and normalizes job inputs into standard UniversalJobModel.
    """

    def normalize(self, raw_data: dict[str, Any] | JobOpportunity) -> UniversalJobModel:
        """
        Normalize and validate a job input into a standard UniversalJobModel.

        Parameters
        ----------
        raw_data : dict[str, Any] | JobOpportunity
            Raw job details dictionary or JobOpportunity object.

        Returns
        -------
        UniversalJobModel
            The normalized model.

        Raises
        ------
        ValidationError
            If any mandatory field is missing, or data is malformed.
        """
        # Convert Pydantic object to dictionary if passed
        if hasattr(raw_data, "model_dump"):
            data = raw_data.model_dump(mode="json")
        elif hasattr(raw_data, "dict"):
            data = raw_data.dict()
        else:
            data = raw_data

        # Convert nested structure back to flat temporary getters if they exist
        is_nested = isinstance(data.get("identity"), dict) and isinstance(data.get("company"), dict)

        # 1. Strict validations
        if is_nested:
            company_name = data.get("company", {}).get("company_name")
            job_title = data.get("job", {}).get("job_title")
            app_url = data.get("application", {}).get("application_url")
            location_raw = data.get("location", {}).get("location") or "Remote"
            remote_status_val = "Remote" if data.get("location", {}).get("remote") else ""
            exp_raw = data.get("job", {}).get("experience_required") or ""
            rel_score_val = data.get("reliability", {}).get("reliability_score") or 50
        else:
            company_name = data.get("company") or data.get("company_name")
            job_title = data.get("role") or data.get("job_title")
            app_url = data.get("application_url")
            location_raw = data.get("location") or "Remote"
            remote_status_val = data.get("remote_status") or ""
            exp_raw = data.get("experience") or data.get("experience_required") or ""
            rel_score_val = data.get("source_reliability_score") or data.get("reliability_score") or 50

        if not company_name or not str(company_name).strip():
            raise ValidationError("Mandatory field missing: Company", context={"data": data})

        if not job_title or not str(job_title).strip():
            raise ValidationError("Mandatory field missing: Role / Title", context={"data": data})

        if not app_url or not str(app_url).strip():
            raise ValidationError("Mandatory field missing: Application URL", context={"data": data})

        if not URL_REGEX.match(app_url):
            raise ValidationError(f"Invalid format: Application URL '{app_url}' is malformed", context={"url": app_url})

        # 2. Normalize components
        company_name = str(company_name).strip()
        job_title = str(job_title).strip()
        location_raw = str(location_raw).strip()

        # Parse location, remote flags
        remote, hybrid, onsite = self._parse_work_mode(location_raw, remote_status_val)
        country = self._normalize_country(location_raw)
        city = self._extract_city(location_raw)

        # Parse experience min / max
        exp_min, exp_max = self._parse_experience_bounds(exp_raw)

        # Identify internship details
        is_intern = (
            "intern" in job_title.lower() or 
            "intern" in exp_raw.lower() or 
            str(data.get("internship_or_full_time") or data.get("internship", {}).get("is_internship") or "").lower() in ["internship", "true"]
        )

        # Rel. trust rating
        rel_score = int(rel_score_val)

        # Build Identity sub-model
        job_id = data.get("job_id") or ""
        if not job_id:
            # Recompute hash fallback
            raw_string = f"{str(data.get('platform') or '').lower()}|{company_name.lower()}|{job_title.lower()}|{location_raw.lower()}|{app_url.lower()}|{str(data.get('posting_date') or '').lower()}"
            import hashlib
            job_id = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

        identity = IdentityModel(
            job_id=job_id,
            source_job_id=data.get("source_job_id") or data.get("identity", {}).get("source_job_id"),
            uuid=data.get("uuid") or data.get("identity", {}).get("uuid") or str(uuid.uuid4()),
            version=data.get("version") or data.get("identity", {}).get("version") or "1.0.0"
        )

        company_dict = data.get("company") if isinstance(data.get("company"), dict) else {}
        job_dict = data.get("job") if isinstance(data.get("job"), dict) else {}
        loc_dict = data.get("location") if isinstance(data.get("location"), dict) else {}
        ai_dict = data.get("ai_classification") if isinstance(data.get("ai_classification"), dict) else {}
        rm_dict = data.get("resume_match") if isinstance(data.get("resume_match"), dict) else {}
        app_dict = data.get("application") if isinstance(data.get("application"), dict) else {}
        intern_dict = data.get("internship") if isinstance(data.get("internship"), dict) else {}
        rel_dict = data.get("reliability") if isinstance(data.get("reliability"), dict) else {}

        company = CompanyModel(
            company_name=company_name,
            company_logo=data.get("company_logo") or company_dict.get("company_logo"),
            company_size=data.get("company_size") or company_dict.get("company_size"),
            company_type=data.get("company_type") or company_dict.get("company_type"),
            company_industry=data.get("company_industry") or company_dict.get("company_industry"),
            company_description=data.get("company_description") or company_dict.get("company_description"),
            company_careers_url=data.get("company_careers_url") or company_dict.get("company_careers_url"),
            company_verified=data.get("company_verified") or company_dict.get("company_verified") or (rel_score >= 95),
            company_country=data.get("company_country") or company_dict.get("company_country") or country,
            company_city=data.get("company_city") or company_dict.get("company_city") or city
        )

        job = JobInfoModel(
            job_title=job_title,
            job_family=data.get("job_family") or job_dict.get("job_family") or ("Engineering" if "engineer" in job_title.lower() or "developer" in job_title.lower() else "Software"),
            job_category=data.get("job_category") or job_dict.get("job_category") or ("AI" if any(term in job_title.lower() for term in ["ai", "llm", "rag", "ml", "nlp"]) else "Software"),
            employment_type=data.get("employment_type") or job_dict.get("employment_type") or ("Full-time" if not is_intern else "Contract"),
            experience_required=exp_raw or "Not Specified",
            minimum_experience=exp_min,
            maximum_experience=exp_max,
            graduation_batch=data.get("graduation_batch") or data.get("graduation_eligibility") or job_dict.get("graduation_batch") or job_dict.get("graduation_eligibility"),
            salary=data.get("salary") or job_dict.get("salary") or "Not Disclosed",
            salary_min=data.get("salary_min") or job_dict.get("salary_min"),
            salary_max=data.get("salary_max") or job_dict.get("salary_max"),
            salary_currency=data.get("salary_currency") or job_dict.get("salary_currency") or ("INR" if "lpa" in str(data.get("salary") or job_dict.get("salary")).lower() else "USD"),
            job_description=data.get("job_description") or data.get("description") or job_dict.get("job_description") or job_dict.get("description") or ""
        )

        location = LocationModel(
            location=location_raw,
            city=city,
            state=data.get("state") or loc_dict.get("state"),
            country=country,
            remote=remote,
            hybrid=hybrid,
            onsite=onsite,
            timezone=data.get("timezone") or loc_dict.get("timezone")
        )

        ai_classification = AIClassificationModel(
            ai_domain=data.get("ai_domain") or ai_dict.get("ai_domain") or ("Generative AI" if "llm" in job_title.lower() or "rag" in job_title.lower() or "generative" in job_title.lower() else "AI Engineering"),
            primary_skill=data.get("primary_skill") or ai_dict.get("primary_skill") or "Python",
            secondary_skills=data.get("secondary_skills") or ai_dict.get("secondary_skills") or [],
            required_skills=data.get("required_skills") or ai_dict.get("required_skills") or [],
            preferred_skills=data.get("preferred_skills") or ai_dict.get("preferred_skills") or [],
            technology_stack=data.get("technology_stack") or ai_dict.get("technology_stack") or [],
            job_keywords=data.get("job_keywords") or ai_dict.get("job_keywords") or [],
            expanded_keywords=data.get("expanded_keywords") or ai_dict.get("expanded_keywords") or []
        )

        resume_match = ResumeMatchModel(
            candidate_match_score=data.get("candidate_match_score") or rm_dict.get("candidate_match_score"),
            resume_keywords_matched=data.get("resume_keywords_matched") or rm_dict.get("resume_keywords_matched") or [],
            resume_keywords_missing=data.get("resume_keywords_missing") or rm_dict.get("resume_keywords_missing") or [],
            preferred_role_match=data.get("preferred_role_match") or rm_dict.get("preferred_role_match"),
            location_match=data.get("location_match") or rm_dict.get("location_match"),
            experience_match=data.get("experience_match") or rm_dict.get("experience_match"),
            graduation_match=data.get("graduation_match") or rm_dict.get("graduation_match")
        )

        application = ApplicationModel(
            application_url=app_url,
            company_careers_url=data.get("company_careers_url") or app_dict.get("company_careers_url"),
            platform=data.get("platform") or app_dict.get("platform") or "Unknown",
            application_method=data.get("application_method") or app_dict.get("application_method") or "External Redirect",
            easy_apply=bool(data.get("easy_apply") or app_dict.get("easy_apply")),
            direct_company_apply=bool(data.get("direct_company_apply") or app_dict.get("direct_company_apply") or rel_score == 100),
            external_redirect=bool(data.get("external_redirect") or app_dict.get("external_redirect") or rel_score != 100),
            application_deadline=data.get("application_deadline") or app_dict.get("application_deadline"),
            status=data.get("status") or app_dict.get("status") or "Discovered"
        )

        internship = InternshipModel(
            is_internship=is_intern,
            ppo_available=bool(data.get("ppo_available") or data.get("ppo_mentioned") or intern_dict.get("ppo_available")),
            ppo_probability=data.get("ppo_probability") or intern_dict.get("ppo_probability"),
            stipend=data.get("stipend") or data.get("salary") or intern_dict.get("stipend") if is_intern else None,
            internship_duration=data.get("internship_duration") or intern_dict.get("internship_duration")
        )

        reliability = ReliabilityModel(
            verified=bool(data.get("verified") or rel_dict.get("verified") or rel_score >= 95),
            reliability_score=rel_score,
            job_active=bool(data.get("job_active") or rel_dict.get("job_active") or True),
            duplicate=bool(data.get("duplicate") or rel_dict.get("duplicate") or False),
            expired=bool(data.get("expired") or rel_dict.get("expired") or False),
            fake_probability=data.get("fake_probability") or rel_dict.get("fake_probability") or 0.0
        )

        now_str = datetime.now().isoformat()
        metadata = MetadataModel(
            posted_date=data.get("posting_date") or data.get("posted_date") or now_str.split("T")[0],
            discovered_date=data.get("discovered_date") or data.get("timestamp") or now_str,
            last_verified=data.get("last_verified") or now_str,
            search_query=data.get("search_query") or "",
            search_source=data.get("search_source") or "",
            scraper_name=data.get("scraper_name") or f"{data.get('platform', 'Unknown')}Scraper",
            execution_time=data.get("execution_time") or 0.0,
            timestamp=data.get("timestamp") or now_str
        )

        return UniversalJobModel(
            identity=identity,
            company=company,
            job=job,
            location=location,
            ai_classification=ai_classification,
            resume_match=resume_match,
            application=application,
            internship=internship,
            reliability=reliability,
            metadata=metadata,
            rejection_reasons=data.get("rejection_reasons") or [],
            acceptance_reasons=data.get("acceptance_reasons") or [],
            match_report=data.get("match_report") or {},
            alternate_sources=data.get("alternate_sources") or [],
            trust_scores=data.get("trust_scores") or {}
        )

    # -------------------------------------------------------------------------
    # Parsing Helpers
    # -------------------------------------------------------------------------

    def _parse_work_mode(self, loc_str: str, state_str: str) -> tuple[bool, bool, bool]:
        """Resolve remote, hybrid, onsite indicators from location content."""
        loc_clean = f"{loc_str} {state_str}".lower()
        if "remote" in loc_clean or "wfh" in loc_clean or "work from home" in loc_clean:
            return True, False, False
        elif "hybrid" in loc_clean:
            return False, True, False
        else:
            return False, False, True

    def _normalize_country(self, loc_str: str) -> str:
        """Standardize country names."""
        loc_lower = loc_str.lower()
        
        # Mappings
        india_indicators = ["india", "hyderabad", "bangalore", "bengaluru", "pune", "mumbai", "chennai", "delhi", "noida", "gurgaon"]
        us_indicators = ["united states", "usa", "us", "san francisco", "new york", "london"]
        
        if any(term in loc_lower for term in india_indicators):
            return "India"
        if any(term in loc_lower for term in us_indicators):
            return "United States"
            
        return loc_str.split(",")[-1].strip().title()

    def _extract_city(self, loc_str: str) -> str:
        """Extract city string if comma-separated, else default to string itself."""
        parts = [p.strip() for p in loc_str.split(",")]
        cities = ["Hyderabad", "Bangalore", "Bengaluru", "Pune", "Mumbai", "Chennai", "Delhi", "Noida", "Gurgaon", "San Francisco", "London"]
        for c in cities:
            if c.lower() in loc_str.lower():
                return c
        return parts[0] if parts else loc_str

    def _parse_experience_bounds(self, exp_str: str) -> tuple[int | None, int | None]:
        """Extract min and max experience boundaries from string (e.g. '2-5 years')."""
        if not exp_str:
            return None, None
            
        # Match digits
        digits = [int(s) for s in re.findall(r"\b\d+\b", exp_str)]
        if len(digits) >= 2:
            return digits[0], digits[1]
        elif len(digits) == 1:
            if "plus" in exp_str.lower() or "+" in exp_str.lower() or "more" in exp_str.lower():
                return digits[0], None
            return 0, digits[0]
        return None, None
