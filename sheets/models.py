"""
sheets/models.py — Redesigned 7-Column Job Record Data Model
=============================================================
Purpose
-------
Defines the canonical Pydantic model for a single job listing row under
the simplified daily Tracker and Analytics Dashboard architecture.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


# ── The exact 7 column headers written to row 1 of the Tracker sheet ──────────
SHEET_HEADERS: list[str] = [
    "Date found",
    "Job title / company",
    "Location",
    "Job type",
    "Confidence Score",
    "Confidence Grade",
    "Confidence Category",
    "Recommendation",
    "Reason",
    "Resume Match",
    "ATS Match",
    "Technology Match",
    "Experience Match",
    "Location Match",
    "Role Match",
    "Trust Score",
    "Official Link Score",
    "Freshness Score",
    "Graduation Score",
    "Apply link",
    "Raw Link",
    "Source",
    "Status",
    "Notes",
]


class JobRecord(BaseModel):
    """
    Canonical representation of a single job listing.
    Maps to the 7-column layout when writing to and reading from Google Sheets.
    """

    job_id: str = Field(default="", description="Unique SHA-256 hash identifier")

    @model_validator(mode="after")
    def generate_job_id_if_empty(self) -> "JobRecord":
        if not self.job_id:
            import hashlib
            raw_str = f"{self.company}|{self.role}|{self.location}|{self.url}"
            self.job_id = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:12]
        return self

    company: str = Field(default="Unknown", description="Name of the hiring company.")
    company_logo: str = Field(default="", description="Company logo image URL.")
    role: str = Field(default="Unknown", description="Job role / title.")
    department: str = Field(default="Engineering", description="Target department.")
    location: str = Field(default="Unknown", description="Job location (city/country or 'Remote').")
    employment_type: str = Field(default="Full-time", description="Full-time, Part-time, Internship, etc.")
    work_mode: str = Field(default="On-site", description="Remote, Hybrid, or On-site.")
    salary: str = Field(default="Not Disclosed", description="Salary or compensation package details.")
    experience: str = Field(default="Not Specified", description="Required years of experience.")
    eligibility: str = Field(default="Unknown", description="Eligibility details / graduation year batch.")
    resume_match: str = Field(default="0.0", description="Resume Match score.")
    ats_score: str = Field(default="0.0", description="ATS score.")
    technology_match: str = Field(default="0.0")
    experience_match: str = Field(default="0.0")
    location_match: str = Field(default="0.0")
    role_match: str = Field(default="0.0")
    trust_score: str = Field(default="0.0")
    official_link_score: str = Field(default="0.0")
    freshness_score: str = Field(default="0.0")
    graduation_score: str = Field(default="0.0")
    confidence_score: str = Field(default="0.0")
    confidence_grade: str = Field(default="")
    confidence_category: str = Field(default="")
    recommendation: str = Field(default="")
    reason: str = Field(default="")
    priority: str = Field(default="Medium", description="Application priority (High, Medium, Low).")
    status: str = Field(default="Not applied", description="Application lifecycle status.")
    current_stage: str = Field(default="Not applied", description="Lifecycle stage.")
    url: str = Field(default="", description="Primary apply link (Official Career Page URL).")
    alternate_link_1: str = Field(default="", description="Alternate apply link 1.")
    alternate_link_2: str = Field(default="", description="Alternate apply link 2.")
    posting_date: str = Field(default="", description="Date when the job was posted.")
    deadline: str = Field(default="", description="Target application deadline.")
    platform: str = Field(default="", description="Discovery platform.")
    recruiter: str = Field(default="", description="Recruiter Name / Contact information.")
    recruiter_email: str = Field(default="", description="Recruiter email address.")
    source: str = Field(default="", description="Source platform.")
    technologies: str = Field(default="", description="Technology keywords.")
    required_skills: str = Field(default="", description="Required candidate skills.")
    preferred_skills: str = Field(default="", description="Preferred/optional candidate skills.")
    why_recommended: str = Field(default="", description="Why this role is recommended.")
    application_date: str = Field(default="", description="Date applied.")
    oa_date: str = Field(default="", description="Date of Online Assessment.")
    interview_date: str = Field(default="", description="Date of interviews.")
    offer_date: str = Field(default="", description="Date offer received.")
    current_notes: str = Field(default="", description="Free-form user/pipeline notes + status history flow.")
    missing_skills: str = Field(default="", description="Missing candidate skills.")
    last_verified: str = Field(default="", description="Timestamp when last verified.")
    link_health: str = Field(default="Good", description="Apply link active/HTTP health status.")
    evidence_score: str = Field(default="0.0", description="Evidence/verification score.")
    created: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date record was created."
    )
    updated: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date record was updated."
    )

    @field_validator("company", "role", "location", mode="before")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        cleaned = str(v).strip()
        if not cleaned:
            return "Unknown"
        return cleaned

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        """Validate and normalize status to Tracker dropdown options."""
        cleaned = str(v).strip().lower()
        mapping = {
            "not applied": "Not applied",
            "applied": "Applied",
            "skip": "Skip",
            "needs manual review": "Needs Manual Review",
            "manual review": "Needs Manual Review",
            "new": "Not applied",
            "saved": "Not applied",
            "discovered": "Not applied"
        }
        return mapping.get(cleaned, "Not applied")

    def to_row(self) -> list[Any]:
        """Convert record fields to list values matching the Tracker headers."""
        # 1. Date found (created or posting date)
        date_str = self.created or date.today().isoformat()
        
        # 2. Job title / company
        jt_company = f"{self.role} — {self.company}"
        
        # 3. Match score (decimal fraction for percentage formatting, e.g., 0.85)
        try:
            val_str = str(self.resume_match).replace("%", "").strip()
            score = float(val_str)
            if score > 1.0:
                score = score / 100.0
        except ValueError:
            score = 0.0
            
        # 4. Rich job details
        notes_source = " ".join(
            [
                str(self.current_notes or ""),
                str(self.why_recommended or ""),
                str(self.work_mode or ""),
                str(self.link_health or ""),
            ]
        ).lower()
        if self.work_mode in ("Remote", "Hybrid", "On-site"):
            work_mode = self.work_mode
        elif "hybrid" in notes_source:
            work_mode = "Hybrid"
        elif self.location.lower() == "remote" or "remote" in notes_source or "work from home" in notes_source:
            work_mode = "Remote"
        elif "office" in notes_source or "on-site" in notes_source or "onsite" in notes_source:
            work_mode = "On-site"
        else:
            work_mode = "On-site"

        m_skills = self.missing_skills or self.technologies or ""
        
        # 5. Apply link formula
        # If url is already a formula, use it; otherwise wrap it in HYPERLINK
        url_raw = self.url
        # strip formula wrapper if present to get clean URL
        match = re.search(r'=HYPERLINK\("([^"]+)"', url_raw, re.IGNORECASE)
        if match:
            url_raw = match.group(1)
        apply_formula = f'=HYPERLINK("{url_raw}", "Open")' if url_raw else ""
        
        status_val = self.status or "Not applied"
        notes_val = self.current_notes or self.why_recommended or ""

        return [
            date_str,
            jt_company,
            self.location,
            self.employment_type or "Full-time",
            self.confidence_score,
            self.confidence_grade,
            self.confidence_category,
            self.recommendation,
            self.reason,
            self.resume_match,
            self.ats_score,
            self.technology_match,
            self.experience_match,
            self.location_match,
            self.role_match,
            self.trust_score,
            self.official_link_score,
            self.freshness_score,
            self.graduation_score,
            apply_formula,
            url_raw,
            self.platform or self.source,
            status_val,
            notes_val,
        ]

    @classmethod
    def from_row(cls, row: list[Any]) -> "JobRecord":
        """Construct a JobRecord from a raw Tracker row list."""
        padded = list(row) + [""] * (len(SHEET_HEADERS) - len(row))
        
        date_found = padded[0] or date.today().isoformat()
        if isinstance(date_found, (int, float)):
            from datetime import timedelta, date as dt_date
            base_date = dt_date(1899, 12, 30)
            date_found = (base_date + timedelta(days=int(date_found))).isoformat()
        else:
            date_found_str = str(date_found).strip()
            if date_found_str.isdigit():
                from datetime import timedelta, date as dt_date
                base_date = dt_date(1899, 12, 30)
                date_found = (base_date + timedelta(days=int(date_found_str))).isoformat()
            else:
                date_found = date_found_str

        jt_company = padded[1] or "Unknown — Unknown"
        location_val = padded[2]
        employment_type = padded[3]
        confidence_score = padded[4]
        confidence_grade = padded[5]
        confidence_category = padded[6]
        recommendation = padded[7]
        reason = padded[8]
        resume_match = padded[9]
        ats_score = padded[10]
        technology_match = padded[11]
        experience_match = padded[12]
        location_match = padded[13]
        role_match = padded[14]
        trust_score = padded[15]
        official_link_score = padded[16]
        freshness_score = padded[17]
        graduation_score = padded[18]
        apply_link_formula = padded[19]
        raw_link = padded[20]
        source_val = padded[21]
        status_val = padded[22] or "Not applied"
        notes_val = padded[23]
        
        # Try to parse the URL out of the hyperlink formula
        url_clean = ""
        if raw_link:
            url_clean = raw_link
        elif apply_link_formula:
            if apply_link_formula.upper().startswith("=HYPERLINK("):
                import re
                match = re.search(r'=HYPERLINK\("([^"]+)"', apply_link_formula, re.IGNORECASE)
                if match:
                    url_clean = match.group(1)
            else:
                url_clean = str(apply_link_formula).strip()
        
        # Parse job title and company
        if " — " in jt_company:
            role, company = jt_company.split(" — ", 1)
        elif " - " in jt_company:
            role, company = jt_company.split(" - ", 1)
        else:
            role = jt_company
            company = "Unknown"
            
        # url_clean is already handled above.

        return cls(
            company=company.strip(),
            role=role.strip(),
            location=str(location_val or "Unknown").strip(),
            employment_type=str(employment_type or "Full-time").strip(),
            confidence_score=str(confidence_score),
            confidence_grade=str(confidence_grade),
            confidence_category=str(confidence_category),
            recommendation=str(recommendation),
            reason=str(reason),
            resume_match=str(resume_match),
            ats_score=str(ats_score),
            technology_match=str(technology_match),
            experience_match=str(experience_match),
            location_match=str(location_match),
            role_match=str(role_match),
            trust_score=str(trust_score),
            official_link_score=str(official_link_score),
            freshness_score=str(freshness_score),
            graduation_score=str(graduation_score),
            url=url_clean.strip(),
            platform=str(source_val or "").strip(),
            status=status_val,
            current_stage=status_val,
            current_notes=notes_val,
            created=date_found,
            posting_date=date_found
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRecord":
        """Construct a JobRecord from a dictionary, mapping alternate field name keys."""
        mapped = {}
        for k, v in data.items():
            norm_k = k.lower().replace(" ", "_").replace("%", "").strip()
            if norm_k == "company_logo_url":
                norm_k = "company_logo"
            elif norm_k == "official_career_link":
                norm_k = "url"
            elif norm_k == "recruiter_name" or norm_k == "recruiter_linkedin":
                norm_k = "recruiter"
            elif norm_k == "created_date":
                norm_k = "created"
            elif norm_k == "updated_date":
                norm_k = "updated"
            elif norm_k == "ats_match":
                norm_k = "ats_score"
            elif norm_k == "notes":
                norm_k = "current_notes"
            elif norm_k == "date_found":
                norm_k = "created"
            elif norm_k == "job_title_company":
                # If we get "Job title / company" directly, split it
                jt_val = str(v)
                if " — " in jt_val:
                    role_val, comp_val = jt_val.split(" — ", 1)
                    mapped["role"] = role_val.strip()
                    mapped["company"] = comp_val.strip()
                elif " - " in jt_val:
                    role_val, comp_val = jt_val.split(" - ", 1)
                    mapped["role"] = role_val.strip()
                    mapped["company"] = comp_val.strip()
                else:
                    mapped["role"] = jt_val.strip()
                continue
            
            mapped[norm_k] = v

        # Extract url from formula if set
        url_val = mapped.get("url") or mapped.get("official_apply_link") or mapped.get("apply_link") or ""
        if isinstance(url_val, str) and url_val.lower().startswith("=hyperlink"):
            match = re.search(r'=HYPERLINK\("([^"]+)"', url_val, re.IGNORECASE)
            if match:
                url_val = match.group(1)

        # Extract missing skills
        missing_skills_val = mapped.get("missing_skills") or mapped.get("technologies") or ""
        if isinstance(missing_skills_val, list):
            missing_skills_val = ", ".join(missing_skills_val)

        return cls(
            job_id=mapped.get("job_id", ""),
            company=mapped.get("company") or "Unknown",
            company_logo=mapped.get("company_logo", ""),
            role=mapped.get("role") or "Unknown",
            department=mapped.get("department", "Engineering"),
            location=mapped.get("location", "Unknown"),
            employment_type=mapped.get("employment_type", "Full-time"),
            work_mode=mapped.get("work_mode") or mapped.get("remote_status") or "On-site",
            salary=mapped.get("salary", "Not Disclosed"),
            experience=mapped.get("experience", "Not Specified"),
            eligibility=mapped.get("eligibility", "Unknown"),
            resume_match=str(mapped.get("resume_match") or mapped.get("candidate_match_score") or "0.0"),
            ats_score=str(mapped.get("ats_score", "0.0")),
            ai_match=str(mapped.get("ai_match", "0.0")),
            trust_score=str(mapped.get("trust_score", "50.0")),
            priority=mapped.get("priority", "Medium"),
            status=mapped.get("status", "Not applied"),
            current_stage=mapped.get("current_stage") or mapped.get("status") or "Not applied",
            url=url_val,
            alternate_link_1=mapped.get("alternate_link_1", ""),
            alternate_link_2=mapped.get("alternate_link_2", ""),
            posting_date=mapped.get("posting_date", ""),
            deadline=mapped.get("deadline", ""),
            platform=mapped.get("platform", ""),
            recruiter=mapped.get("recruiter", ""),
            recruiter_email=mapped.get("recruiter_email", ""),
            source=mapped.get("source", ""),
            technologies=mapped.get("technologies", ""),
            required_skills=mapped.get("required_skills", ""),
            preferred_skills=mapped.get("preferred_skills", ""),
            why_recommended=mapped.get("why_recommended", ""),
            application_date=mapped.get("application_date", ""),
            oa_date=mapped.get("oa_date", ""),
            interview_date=mapped.get("interview_date", ""),
            offer_date=mapped.get("offer_date", ""),
            current_notes=mapped.get("current_notes") or mapped.get("notes") or "",
            missing_skills=missing_skills_val,
            last_verified=mapped.get("last_verified", ""),
            link_health=mapped.get("link_health", "Good"),
            evidence_score=str(mapped.get("evidence_score", "0.0")),
            created=mapped.get("created") or date.today().isoformat(),
            updated=mapped.get("updated") or date.today().isoformat()
        )

    def dedup_key(self) -> tuple[str, str, str, str]:
        """Deduplication key."""
        loc_val = self.location.lower().strip() if self.location else "unknown"
        return (
            self.company.lower().strip(),
            self.role.lower().strip(),
            loc_val,
            self.url.lower().strip()
        )
