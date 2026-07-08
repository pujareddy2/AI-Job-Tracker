"""
filters/confidence_engine.py — Phase 20 Confidence Scoring Engine
=================================================================
Calculates a comprehensive 0-100 Confidence Score based on 10 distinct dimensions.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from job_model.universal_model import UniversalJobModel, ConfidenceModel
from resume_optimizer.ats_scorer import ATSScorer
from resume_optimizer.config import OptimizerConfig
from config import settings


class ConfidenceEngine:
    def __init__(self):
        self.ats_scorer = ATSScorer(config=OptimizerConfig())
        self.profile = self._load_profile()

    def _load_profile(self) -> dict[str, Any]:
        profile_path = settings.cache_dir / "candidate_profile.json"
        if profile_path.exists():
            return json.loads(profile_path.read_text(encoding="utf-8"))
        return {}

    def score_job(self, job: UniversalJobModel) -> UniversalJobModel:
        """Scores a job and populates its confidence model."""
        
        # 1. Resume Match (30%)
        resume_score = self._score_resume(job)
        
        # 2. ATS Match (15%)
        # Calculate full ATS score (0-100) and scale to 15
        ats_full = 0.0
        try:
            ats_report = self.ats_scorer.score(
                profile=self.profile,
                job_id=job.identity.job_id,
                job_title=job.job.job_title,
                company_name=job.company.company_name,
                job_description=job.job.description,
                job_required_skills=job.job.skills,
                job_tech_stack=job.job.technologies,
                job_keywords=job.job.keywords,
                job_location=job.location.location,
                job_remote=job.location.remote,
                job_min_exp=job.job.minimum_experience,
                job_reliability=job.reliability.reliability_score,
                candidate_match_score=job.resume_match.match_score
            )
            ats_full = ats_report.overall_ats_score
        except Exception:
            pass
        ats_score = round((ats_full / 100.0) * 15, 2)
        
        # 3. Technology Match (15%)
        tech_score = self._score_technology(job)
        
        # 4. Experience Match (10%)
        exp_score = self._score_experience(job)
        
        # 5. Location Match (5%)
        loc_score = self._score_location(job)
        
        # 6. Role Match (10%)
        role_score = self._score_role(job)
        
        # 7. Company Trust (5%)
        trust_score = self._score_trust(job)
        
        # 8. Official Link (5%)
        link_score = self._score_official_link(job)
        
        # 9. Freshness (3%)
        fresh_score = self._score_freshness(job)
        
        # 10. Graduation Eligibility (2%)
        grad_score = self._score_graduation(job)

        # Total Calculation
        overall = sum([
            resume_score, ats_score, tech_score, exp_score, loc_score,
            role_score, trust_score, link_score, fresh_score, grad_score
        ])
        overall = min(100.0, max(0.0, round(overall, 2)))

        # Classification
        if overall >= 95:
            grade = "★★★★★"
            cat = "Dream Job"
            rec = "Apply Today"
        elif overall >= 90:
            grade = "★★★★★"
            cat = "Excellent Match"
            rec = "Apply Today"
        elif overall >= 80:
            grade = "★★★★☆"
            cat = "Strong Match"
            rec = "High Priority"
        elif overall >= 70:
            grade = "★★★★"
            cat = "Good Match"
            rec = "Apply This Week"
        elif overall >= 60:
            grade = "★★★"
            cat = "Worth Applying"
            rec = "Optional"
        elif overall >= 50:
            grade = "★★"
            cat = "Manual Review"
            rec = "Skip"
        else:
            grade = "★"
            cat = "Reject"
            rec = "Skip"

        # Generate Explanation
        explanation = f"Confidence {overall}%. "
        strongest = []
        if tech_score >= 12: strongest.append("Top AI/Tech Stack Match")
        if resume_score >= 25: strongest.append("Perfect Resume Alignment")
        if loc_score == 5: strongest.append("Ideal Location")
        if ats_score >= 12: strongest.append("High ATS Compatibility")
        explanation += " | ".join(strongest[:2]) if strongest else "Average Match."

        job.confidence = ConfidenceModel(
            overall_score=overall,
            grade=grade,
            category=cat,
            recommendation=rec,
            reason=explanation,
            resume_match_score=resume_score,
            ats_match_score=ats_score,
            technology_match_score=tech_score,
            experience_match_score=exp_score,
            location_match_score=loc_score,
            role_match_score=role_score,
            trust_score=trust_score,
            official_link_score=link_score,
            freshness_score=fresh_score,
            graduation_score=grad_score
        )
        return job

    def _score_resume(self, job: UniversalJobModel) -> float:
        # Scale based on AI keywords in profile vs job description
        # 30 points max
        desc = job.job.job_description.lower()
        keywords = ["python", "genai", "llm", "backend", "fastapi", "langchain", "rag", "automation"]
        matched = sum(1 for k in keywords if k in desc)
        score = (matched / len(keywords)) * 30
        return min(30.0, round(score, 2))

    def _score_technology(self, job: UniversalJobModel) -> float:
        desc = job.job.job_description.lower()
        families = {
            "Python": ["python", "fastapi", "flask", "django", "asyncio"],
            "LLM": ["openai", "claude", "anthropic", "gemini", "llama", "mistral"],
            "RAG": ["vector search", "embeddings", "faiss", "pinecone", "milvus", "chroma"],
            "Backend": ["rest api", "microservices", "fastapi", "postgresql", "redis"]
        }
        matched_families = 0
        for f, kws in families.items():
            if any(k in desc for k in kws):
                matched_families += 1
        score = (matched_families / len(families)) * 15
        return min(15.0, round(score, 2))

    def _score_experience(self, job: UniversalJobModel) -> float:
        desc = job.job.job_description.lower()
        title = job.job.job_title.lower()
        
        reject_terms = ["3+ years", "4+ years", "lead", "senior", "principal"]
        if any(term in title or term in desc for term in reject_terms):
            return 0.0

        if any(term in desc for term in ["graduate", "entry level", "associate", "freshers", "campus", "0-1 year", "0-2 year"]):
            return 10.0
        if "preferred 1 year" in desc:
            return 7.0
        if "2 years" in desc:
            return 3.0
        return 10.0  # Default assume entry level if no red flags

    def _score_location(self, job: UniversalJobModel) -> float:
        loc = job.location.location.lower()
        if job.location.remote and "india" in loc: return 5.0
        if "hyderabad" in loc: return 5.0
        if any(city in loc for city in ["bangalore", "pune", "chennai", "delhi ncr"]): return 4.0
        if loc == "india": return 3.0
        if job.location.country == "india": return 2.0
        return 0.0

    def _score_role(self, job: UniversalJobModel) -> float:
        title = job.job.job_title.lower()
        roles = ["applied ai", "ai engineer", "genai", "machine learning", "llm", "backend ai", "python ai", "ai product engineer", "automation engineer", "agentic ai", "ai platform", "conversational ai"]
        if any(r in title for r in roles):
            return 10.0
        if "engineer" in title or "developer" in title:
            return 5.0
        return 0.0

    def _score_trust(self, job: UniversalJobModel) -> float:
        if job.company.company_careers_url:
            return 5.0
        if "linkedin.com/company" in (job.application.application_url or "").lower():
            return 4.0
        if job.application.application_url:
            return 3.0
        return 0.0

    def _score_official_link(self, job: UniversalJobModel) -> float:
        url = (job.application.application_url or "").lower()
        if "careers." in url or "jobs." in url or job.application.direct_company_apply:
            return 5.0
        if "linkedin.com/jobs" in url:
            return 4.0
        if "indeed.com" in url or "naukri.com" in url:
            return 4.0
        if url:
            return 2.0
        return 0.0

    def _score_freshness(self, job: UniversalJobModel) -> float:
        try:
            if not job.metadata.posted_date:
                return 0.0
            posted = job.metadata.posted_date.lower()
            if "hour" in posted or "today" in posted or "just now" in posted:
                return 3.0
            if "1 day" in posted or "2 day" in posted or "3 day" in posted:
                return 2.5
            if "day" in posted: # 4+ days
                return 2.0
            if "week" in posted:
                return 1.0
            return 0.0
        except Exception:
            return 0.0

    def _score_graduation(self, job: UniversalJobModel) -> float:
        desc = job.job.job_description.lower()
        reject_terms = ["2025 only", "2026 only", "experienced only", "2022 batch", "2023 batch"]
        if any(term in desc for term in reject_terms):
            return 0.0
        if any(term in desc for term in ["fresher", "graduate", "recent graduate"]):
            return 2.0
        return 1.5
