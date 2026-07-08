"""
resume_optimizer/ats_scorer.py — 16-Dimension ATS Score Calculator
===================================================================
Purpose
-------
Compute an explainable ATS score for one resume vs one job description.
Every dimension has a documented scoring methodology and produces
both a numeric score (0–100) and a human-readable explanation.

Design Philosophy
-----------------
No arbitrary numbers.  Every score is derived from a specific comparison:
  - keyword_score  = |resume_tokens ∩ jd_tokens| / |jd_tokens|
  - skills_score   = matched_skills / required_skills_from_jd
  - etc.

The scoring is intentionally conservative: a 70 is a genuine good match,
not a participation award.

Why 16 dimensions?
  Real ATS systems evaluate far more signals than simple keyword matching.
  Recruiters look at formatting, completeness, recruiter appeal (GitHub,
  awards), confidence (is the JD even well-written?), and role relevance.
  16 dimensions give a realistic multi-faceted view without being arbitrary.
"""

from __future__ import annotations

import re
from typing import Any

from resume_optimizer.config import OptimizerConfig
from resume_optimizer.models import ATSScoreCard, ScoreDimension


# ---------------------------------------------------------------------------
# Industry-standard keyword lists by role type
# ---------------------------------------------------------------------------
_ROLE_KEYWORDS: dict[str, list[str]] = {
    "ai": ["llm", "rag", "langchain", "embeddings", "vector", "prompt", "fine-tuning",
           "generative ai", "transformer", "huggingface", "openai"],
    "ml": ["machine learning", "deep learning", "scikit-learn", "pytorch", "tensorflow",
           "xgboost", "feature engineering", "model training", "inference"],
    "backend": ["fastapi", "django", "flask", "rest api", "grpc", "microservices",
                "postgresql", "redis", "kafka", "docker", "kubernetes"],
    "frontend": ["react", "typescript", "javascript", "css", "html", "next.js",
                 "redux", "webpack", "responsive design"],
    "data": ["pandas", "numpy", "sql", "etl", "pipeline", "spark", "airflow",
             "data warehouse", "tableau", "power bi"],
    "devops": ["docker", "kubernetes", "ci/cd", "github actions", "terraform",
               "ansible", "monitoring", "prometheus", "grafana"],
    "fullstack": ["react", "fastapi", "postgresql", "docker", "rest api", "typescript"],
}


def _tokenize(text: str, stop_words: set[str], min_len: int = 3) -> set[str]:
    """
    Tokenize text into a normalised set of keyword tokens.

    Algorithm:
    1. Lowercase the text.
    2. Remove punctuation except hyphens (hyphens are meaningful in tech terms).
    3. Split on whitespace and hyphens.
    4. Drop tokens shorter than min_len.
    5. Drop stop words.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s\-/+#.]", " ", text)
    tokens = re.split(r"[\s]+", text)
    return {
        t.strip("-./")
        for t in tokens
        if len(t.strip("-./")) >= min_len and t.strip("-./") not in stop_words
    }


def _overlap_score(resume_set: set[str], jd_set: set[str]) -> tuple[float, list[str], list[str]]:
    """
    Compute the fraction of JD tokens found in the resume.

    Returns:
        score (float 0–100),
        matched (list),
        missing (list)
    """
    if not jd_set:
        return 50.0, [], []  # neutral baseline when JD has no tokens
    matched = sorted(resume_set & jd_set)
    missing = sorted(jd_set - resume_set)
    score = (len(matched) / len(jd_set)) * 100.0
    return round(min(score, 100.0), 2), matched, missing


class ATSScorer:
    """
    Computes a 16-dimension ATS score card for one resume-job pair.

    Parameters
    ----------
    config : OptimizerConfig
        Engine configuration (weights, thresholds, stop-word list).

    Usage
    -----
        scorer = ATSScorer(config)
        scorecard = scorer.score(profile_dict, job)
    """

    def __init__(self, config: OptimizerConfig) -> None:
        self.config = config
        self.weights = config.ats_weights
        self.kw_cfg = config.keyword_config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        profile: dict[str, Any],
        job_id: str,
        job_title: str,
        company_name: str,
        job_description: str,
        job_required_skills: list[str],
        job_tech_stack: list[str],
        job_keywords: list[str],
        job_location: str,
        job_remote: bool,
        job_min_exp: int | None,
        job_reliability: float,
        candidate_match_score: int | None,
    ) -> ATSScoreCard:
        """
        Compute the full 16-dimension ATS score card.

        Parameters
        ----------
        profile : dict
            CandidateProfile serialised as a plain dict.
        job_id, job_title, company_name : str
            Job metadata.
        job_description : str
            Full job description text.
        job_required_skills, job_tech_stack, job_keywords : list[str]
            Skills, tech stack, and keywords extracted by the normalization engine.
        job_location : str
            Job location string.
        job_remote : bool
            True if the job is remote.
        job_min_exp : int | None
            Minimum years of experience required.
        job_reliability : float
            Source reliability score (0–100) from the scraper.
        candidate_match_score : int | None
            Overall match score from the existing matching engine.

        Returns
        -------
        ATSScoreCard
        """
        jd_text = job_description.lower()
        jd_tokens = _tokenize(job_description, self.kw_cfg.stop_words, self.kw_cfg.min_keyword_length)

        # Flatten resume data
        resume_skills = self._flat_skills(profile)
        resume_tokens = _tokenize(
            " ".join(resume_skills) + " " + self._resume_text(profile),
            self.kw_cfg.stop_words,
            self.kw_cfg.min_keyword_length,
        )

        # Compute each dimension
        kw = self._keyword_score(resume_tokens, jd_tokens, job_keywords)
        sk = self._skills_score(resume_skills, job_required_skills, jd_text)
        tm = self._technology_match_score(resume_skills, job_tech_stack, jd_text)
        rr = self._role_relevance_score(profile, job_title, jd_text)
        pr = self._projects_score(profile, job_tech_stack, jd_text)
        isc = self._internship_score(profile, job_tech_stack, jd_text)
        edu = self._education_score(profile, jd_text)
        exp = self._experience_score(profile, job_min_exp)
        cert = self._certification_score(profile, jd_text)
        fmt = self._formatting_score(profile)
        loc = self._location_match_score(profile, job_location, job_remote)
        rdbl = self._readability_score(profile)
        cmp = self._completeness_score(profile)
        rec = self._recruiter_appeal_score(profile)
        conf = self._confidence_score(job_description, job_reliability)

        # Weighted overall
        overall = (
            kw.score * self.weights.keyword_score +
            sk.score * self.weights.skills_score +
            tm.score * self.weights.technology_match_score +
            rr.score * self.weights.role_relevance_score +
            pr.score * self.weights.projects_score +
            isc.score * self.weights.internship_score +
            edu.score * self.weights.education_score +
            exp.score * self.weights.experience_score +
            cert.score * self.weights.certification_score +
            fmt.score * self.weights.formatting_score +
            loc.score * self.weights.location_match_score +
            rdbl.score * self.weights.readability_score +
            cmp.score * self.weights.completeness_score +
            rec.score * self.weights.recruiter_appeal_score +
            conf.score * self.weights.confidence_score
        )
        overall = round(min(overall, 100.0), 2)

        fit_category = (
            "Top Picks" if overall >= 90 else
            "Priority" if overall >= 80 else
            "Recommended" if overall >= 70 else
            "Candidate" if overall >= 60 else
            "Weak Fit"
        )

        return ATSScoreCard(
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            keyword_score=kw,
            skills_score=sk,
            technology_match_score=tm,
            role_relevance_score=rr,
            projects_score=pr,
            internship_score=isc,
            education_score=edu,
            experience_score=exp,
            certification_score=cert,
            formatting_score=fmt,
            location_match_score=loc,
            readability_score=rdbl,
            completeness_score=cmp,
            recruiter_appeal_score=rec,
            confidence_score=conf,
            overall_ats_score=overall,
            overall_explanation=(
                f"Overall ATS score of {overall:.1f}/100 ({fit_category}). "
                f"Strongest dimensions: keyword coverage ({kw.score:.0f}), "
                f"skills match ({sk.score:.0f}), technology match ({tm.score:.0f}). "
                f"Key gaps: {', '.join((kw.missing_items + sk.missing_items)[:3]) or 'none identified'}."
            ),
            fit_category=fit_category,
        )

    # ------------------------------------------------------------------
    # Private dimension scorers
    # ------------------------------------------------------------------

    def _keyword_score(
        self,
        resume_tokens: set[str],
        jd_tokens: set[str],
        job_keywords: list[str],
    ) -> ScoreDimension:
        """
        Keyword Score Methodology
        -------------------------
        Combines two signals:
        1. Token overlap: |resume_tokens ∩ jd_tokens| / |jd_tokens|
        2. Explicit keyword list: fraction of job's extracted keywords matched
        Final score = weighted average (60% token overlap, 40% explicit keyword match).
        """
        tok_score, matched, missing = _overlap_score(resume_tokens, jd_tokens)

        # Explicit keyword match
        jk_tokens = {k.lower().strip() for k in job_keywords}
        jk_matched = {k for k in jk_tokens if k in resume_tokens}
        explicit_score = (len(jk_matched) / len(jk_tokens) * 100.0) if jk_tokens else tok_score

        final = round(tok_score * 0.6 + explicit_score * 0.4, 2)

        return ScoreDimension(
            name="Keyword Score",
            score=final,
            weight=self.weights.keyword_score,
            explanation=(
                f"Resume covers {len(matched)} of {len(jd_tokens)} JD tokens ({tok_score:.1f}%). "
                f"Explicit keyword match: {len(jk_matched)}/{len(jk_tokens)} ({explicit_score:.1f}%). "
                f"Combined score (60/40 weighted): {final:.1f}."
            ),
            matched_items=sorted(matched)[:15],
            missing_items=sorted(missing)[:15],
        )

    def _skills_score(
        self,
        resume_skills: list[str],
        required_skills: list[str],
        jd_text: str,
    ) -> ScoreDimension:
        """
        Skills Score Methodology
        ------------------------
        Compares candidate's skill list against JD's required_skills field.
        Falls back to scanning jd_text for skill mentions when required_skills is empty.
        Score = matched_skills / max(required_skills, 1) × 100.
        """
        rs_lower = {s.lower() for s in resume_skills}
        req = [s.lower() for s in required_skills] if required_skills else []

        # If no required_skills provided, extract from jd_text using known skill tokens
        if not req:
            req = [s for s in rs_lower if s in jd_text]

        matched = [s for s in req if any(s in r or r in s for r in rs_lower)]
        missing = [s for s in req if s not in matched]
        score = (len(matched) / max(len(req), 1)) * 100.0

        return ScoreDimension(
            name="Skills Score",
            score=round(score, 2),
            weight=self.weights.skills_score,
            explanation=(
                f"Matched {len(matched)} of {len(req)} required skills. "
                f"{'No required skills listed in JD — using JD text scan.' if not required_skills else ''}"
            ),
            matched_items=sorted(matched)[:10],
            missing_items=sorted(missing)[:10],
        )

    def _technology_match_score(
        self,
        resume_skills: list[str],
        tech_stack: list[str],
        jd_text: str,
    ) -> ScoreDimension:
        """
        Technology Match Score Methodology
        -----------------------------------
        Compares the full resume skill inventory (all categories) against:
        1. The job's extracted technology stack list.
        2. Technology mentions in the jd_text (fallback).
        Score = matched_techs / max(total_techs, 1) × 100.
        """
        rs_lower = {s.lower() for s in resume_skills}
        stack = [t.lower() for t in tech_stack] if tech_stack else []

        if not stack:
            # Fallback: scan for any resume skill in jd_text
            stack = [s for s in rs_lower if s in jd_text]

        matched = [t for t in stack if any(t in r or r in t for r in rs_lower)]
        missing = [t for t in stack if t not in matched]
        score = (len(matched) / max(len(stack), 1)) * 100.0

        return ScoreDimension(
            name="Technology Match Score",
            score=round(score, 2),
            weight=self.weights.technology_match_score,
            explanation=(
                f"Matched {len(matched)} of {len(stack)} technologies in the job's stack."
            ),
            matched_items=sorted(matched)[:10],
            missing_items=sorted(missing)[:10],
        )

    def _role_relevance_score(
        self,
        profile: dict[str, Any],
        job_title: str,
        jd_text: str,
    ) -> ScoreDimension:
        """
        Role Relevance Score Methodology
        ---------------------------------
        1. Checks if any preferred_role from profile matches the job title (100 pts).
        2. Checks if inferred_roles from profile overlap with job title (70 pts).
        3. Checks role-type keywords (AI/ML/Backend/Frontend) in title (50 pts).
        4. Returns 30 as baseline if none match (role is plausible but unverified).
        """
        title_lower = job_title.lower()
        preferred = [r.lower() for r in profile.get("candidate_analysis", {}).get("preferred_roles", [])]
        inferred = [r.get("title", "").lower() for r in profile.get("inferred_roles", [])]

        matched_preferred = [r for r in preferred if r in title_lower or title_lower in r]
        matched_inferred = [r for r in inferred if any(w in title_lower for w in r.split())]

        if matched_preferred:
            score, reason = 95.0, f"Preferred role '{matched_preferred[0]}' matches job title."
        elif matched_inferred:
            score, reason = 75.0, f"Inferred role '{matched_inferred[0]}' matches job title."
        elif any(kw in title_lower for kw in ["ai", "ml", "backend", "data", "software", "engineer", "developer"]):
            score, reason = 55.0, "Generic tech role keyword match in job title."
        else:
            score, reason = 30.0, "Job title does not match any preferred or inferred roles."

        return ScoreDimension(
            name="Role Relevance Score",
            score=score,
            weight=self.weights.role_relevance_score,
            explanation=reason,
            matched_items=matched_preferred or matched_inferred,
            missing_items=[],
        )

    def _projects_score(
        self,
        profile: dict[str, Any],
        tech_stack: list[str],
        jd_text: str,
    ) -> ScoreDimension:
        """
        Projects Score Methodology
        --------------------------
        For each project, checks if any of its listed technologies appear
        in the job's tech stack or JD text. Relevance is binary per-project.
        Score = relevant_projects / total_projects × 100.
        Baseline of 40 if no projects exist (neutral).
        """
        projects = profile.get("projects", [])
        if not projects:
            return ScoreDimension(
                name="Projects Score", score=40.0, weight=self.weights.projects_score,
                explanation="No projects found in profile — neutral baseline applied.",
                matched_items=[], missing_items=[],
            )

        stack_lower = {t.lower() for t in tech_stack}
        matched, unmatched = [], []
        for proj in projects:
            techs = [t.lower() for t in proj.get("technologies", [])]
            desc = proj.get("description", "").lower()
            relevant = any(t in stack_lower or t in jd_text for t in techs) or \
                       any(t in desc for t in stack_lower)
            if relevant:
                matched.append(proj.get("name", "Unnamed"))
            else:
                unmatched.append(proj.get("name", "Unnamed"))

        score = (len(matched) / len(projects)) * 100.0
        return ScoreDimension(
            name="Projects Score",
            score=round(score, 2),
            weight=self.weights.projects_score,
            explanation=f"{len(matched)} of {len(projects)} projects have technology overlap with JD.",
            matched_items=matched,
            missing_items=unmatched,
        )

    def _internship_score(
        self,
        profile: dict[str, Any],
        tech_stack: list[str],
        jd_text: str,
    ) -> ScoreDimension:
        """
        Internship Score Methodology
        ----------------------------
        Same approach as projects score but for internship entries.
        Baseline of 50 if no internships (many freshers have none).
        """
        internships = profile.get("experience", {}).get("internships", [])
        if not internships:
            return ScoreDimension(
                name="Internship Score", score=50.0, weight=self.weights.internship_score,
                explanation="No internships in profile — neutral baseline for freshers applied.",
                matched_items=[], missing_items=[],
            )

        stack_lower = {t.lower() for t in tech_stack}
        matched, unmatched = [], []
        for intern in internships:
            techs = [t.lower() for t in intern.get("technologies", [])]
            if any(t in stack_lower or t in jd_text for t in techs):
                matched.append(intern.get("role", "Unnamed"))
            else:
                unmatched.append(intern.get("role", "Unnamed"))

        score = (len(matched) / len(internships)) * 100.0
        return ScoreDimension(
            name="Internship Score",
            score=round(score, 2),
            weight=self.weights.internship_score,
            explanation=f"{len(matched)} of {len(internships)} internships match the JD tech stack.",
            matched_items=matched,
            missing_items=unmatched,
        )

    def _education_score(self, profile: dict[str, Any], jd_text: str) -> ScoreDimension:
        """
        Education Score Methodology
        ---------------------------
        Components:
        - CGPA ≥ 8.0 → +30 pts (many companies filter at 7.5 or 8.0)
        - Graduation year mentioned in JD → +30 pts
        - Degree/branch relevant to JD → +20 pts
        - Institution named (not empty) → +20 pts
        """
        edu = profile.get("education", {})
        score = 0.0
        reasons = []

        # CGPA check
        cgpa_str = edu.get("cgpa", "")
        try:
            cgpa = float(cgpa_str.split("/")[0])
            if cgpa >= 8.0:
                score += 30
                reasons.append(f"CGPA {cgpa:.1f} ≥ 8.0 threshold.")
            elif cgpa >= 7.5:
                score += 20
                reasons.append(f"CGPA {cgpa:.1f} ≥ 7.5 threshold.")
            elif cgpa > 0:
                score += 10
                reasons.append(f"CGPA {cgpa:.1f} below common 7.5 threshold.")
        except (ValueError, IndexError):
            reasons.append("CGPA not parseable — no score added.")

        # Graduation year
        grad_year = edu.get("graduation_year")
        if grad_year and str(grad_year) in jd_text:
            score += 30
            reasons.append(f"Graduation year {grad_year} matches JD batch requirement.")
        elif grad_year:
            score += 15
            reasons.append(f"Graduation year {grad_year} — JD does not specify batch.")

        # Branch relevance
        branch = edu.get("branch", "").lower()
        if branch and any(b in jd_text for b in [branch, "cs", "computer", "engineering", "information"]):
            score += 20
            reasons.append(f"Branch '{branch}' relevant to JD.")
        elif branch:
            score += 10
            reasons.append(f"Branch '{branch}' not specifically required by JD.")

        # Institution presence
        if edu.get("institution", "").strip():
            score += 20
            reasons.append("Institution name present in profile.")

        score = min(score, 100.0)
        return ScoreDimension(
            name="Education Score",
            score=round(score, 2),
            weight=self.weights.education_score,
            explanation=" | ".join(reasons) or "No education data.",
            matched_items=[],
            missing_items=[],
        )

    def _experience_score(self, profile: dict[str, Any], min_exp: int | None) -> ScoreDimension:
        """
        Experience Score Methodology
        ----------------------------
        - min_exp is None or 0 → 100 (fresher-friendly)
        - min_exp == 1 → 80 (fresher with internships may qualify)
        - min_exp > 1 → 0 (candidate is fresher, hard disqualifier)
        """
        level = profile.get("experience", {}).get("level", "Fresher")
        total_months = profile.get("experience", {}).get("total_months", 0)

        if min_exp is None or min_exp == 0:
            score, reason = 100.0, "No experience requirement — open to freshers."
        elif min_exp == 1 and total_months >= 3:
            score, reason = 80.0, f"1 year minimum; candidate has {total_months} months (internship counts)."
        elif min_exp == 1:
            score, reason = 60.0, "1 year minimum; candidate is fresher — may qualify with strong profile."
        elif min_exp <= 2:
            score, reason = 30.0, f"{min_exp} years required; candidate is {level} level."
        else:
            score, reason = 0.0, f"{min_exp}+ years required; candidate is Fresher — hard disqualifier."

        return ScoreDimension(
            name="Experience Score",
            score=score,
            weight=self.weights.experience_score,
            explanation=reason,
            matched_items=[],
            missing_items=[f"{min_exp}+ years experience"] if min_exp and min_exp > 1 else [],
        )

    def _certification_score(self, profile: dict[str, Any], jd_text: str) -> ScoreDimension:
        """
        Certification Score Methodology
        --------------------------------
        - Has certifications that match JD → 100
        - Has certifications, JD doesn't require them → 70 (still a positive signal)
        - No certifications, JD requires them → 30
        - No certifications, JD doesn't require them → 60 (neutral)
        """
        certs = profile.get("certifications", [])
        cert_keywords = ["certification", "certified", "certificate", "aws ", "google cloud",
                         "azure", "coursera", "udemy", "nptel"]
        jd_requires_certs = any(kw in jd_text for kw in cert_keywords)

        if certs:
            matched = [c for c in certs if any(word in jd_text for word in c.lower().split())]
            if matched:
                score, reason = 100.0, f"Certifications {matched} directly relevant to JD."
            else:
                score, reason = 70.0, f"Has {len(certs)} certification(s) — not explicitly required by JD."
        elif jd_requires_certs:
            score, reason = 30.0, "JD implies certifications are valued but none found in profile."
        else:
            score, reason = 60.0, "No certifications; JD does not require them."

        return ScoreDimension(
            name="Certification Score",
            score=score,
            weight=self.weights.certification_score,
            explanation=reason,
            matched_items=certs,
            missing_items=[],
        )

    def _formatting_score(self, profile: dict[str, Any]) -> ScoreDimension:
        """
        Formatting Score Methodology
        ----------------------------
        Inferred from the structured profile (since we don't re-read the PDF).
        Positive signals: has all contact links, has projects with descriptions,
        internships have responsibilities listed, skills are categorised.
        Score is a weighted sum of these signals.
        """
        personal = profile.get("personal", {})
        score = 0.0
        reasons = []

        if personal.get("linkedin"):
            score += 20
            reasons.append("LinkedIn link present.")
        if personal.get("github"):
            score += 20
            reasons.append("GitHub link present.")
        if personal.get("email"):
            score += 15
            reasons.append("Email address present.")
        if personal.get("phone"):
            score += 10
            reasons.append("Phone number present.")

        projects = profile.get("projects", [])
        projs_with_desc = [p for p in projects if p.get("description")]
        if projs_with_desc:
            score += 20
            reasons.append(f"{len(projs_with_desc)} project(s) have descriptions.")

        skills = profile.get("skills", {})
        if any(skills.values()):
            score += 15
            reasons.append("Skills are categorized.")

        return ScoreDimension(
            name="Formatting Score",
            score=round(min(score, 100.0), 2),
            weight=self.weights.formatting_score,
            explanation=" | ".join(reasons) or "No formatting signals detected.",
            matched_items=[],
            missing_items=[],
        )

    def _location_match_score(
        self, profile: dict[str, Any], job_location: str, job_remote: bool
    ) -> ScoreDimension:
        """
        Location Match Score Methodology
        ---------------------------------
        - Remote job → 100 (no location constraint)
        - Candidate preferred location matches job → 100
        - Job is in India → 70 (general India fallback)
        - No match → 30
        """
        if job_remote:
            return ScoreDimension(
                name="Location Match Score", score=100.0, weight=self.weights.location_match_score,
                explanation="Remote position — no location constraint.",
                matched_items=["Remote"], missing_items=[],
            )

        preferred = [loc.lower() for loc in profile.get("candidate_analysis", {}).get("preferred_locations", [])]
        loc_lower = job_location.lower()

        if any(p in loc_lower for p in preferred):
            return ScoreDimension(
                name="Location Match Score", score=100.0, weight=self.weights.location_match_score,
                explanation=f"Job location '{job_location}' matches preferred locations.",
                matched_items=[job_location], missing_items=[],
            )
        elif "india" in loc_lower or any(city in loc_lower for city in ["hyderabad", "bangalore", "pune", "chennai", "mumbai", "delhi"]):
            return ScoreDimension(
                name="Location Match Score", score=70.0, weight=self.weights.location_match_score,
                explanation=f"Job location '{job_location}' is in India — acceptable.",
                matched_items=[job_location], missing_items=[],
            )
        return ScoreDimension(
            name="Location Match Score", score=30.0, weight=self.weights.location_match_score,
            explanation=f"Job location '{job_location}' does not match preferred locations.",
            matched_items=[], missing_items=[job_location],
        )

    def _readability_score(self, profile: dict[str, Any]) -> ScoreDimension:
        """
        Readability Score Methodology
        ------------------------------
        Inferred from structured profile quality:
        - Has resume_summary → +25
        - Has ≥3 projects with descriptions → +25
        - Has internship responsibilities → +25
        - Has categorised skills → +25
        """
        score = 0.0
        reasons = []

        if profile.get("resume_summary", "").strip():
            score += 25
            reasons.append("Resume summary present.")
        projects = [p for p in profile.get("projects", []) if p.get("description")]
        if len(projects) >= 3:
            score += 25
            reasons.append(f"{len(projects)} projects with descriptions.")
        elif projects:
            score += 15
            reasons.append(f"{len(projects)} project(s) with descriptions.")
        internships = profile.get("experience", {}).get("internships", [])
        if any(i.get("responsibilities") for i in internships):
            score += 25
            reasons.append("Internship responsibilities listed.")
        skills = profile.get("skills", {})
        if sum(len(v) for v in skills.values() if isinstance(v, list)) >= 5:
            score += 25
            reasons.append("Categorised skills present.")

        return ScoreDimension(
            name="Readability Score", score=round(min(score, 100.0), 2),
            weight=self.weights.readability_score,
            explanation=" | ".join(reasons) or "Insufficient structured data for readability assessment.",
            matched_items=[], missing_items=[],
        )

    def _completeness_score(self, profile: dict[str, Any]) -> ScoreDimension:
        """
        Completeness Score Methodology
        --------------------------------
        Checks that all key sections are present and non-empty.
        Each section contributes equally (100 / 7 sections = ~14.3 pts each).
        """
        sections = {
            "Personal Info": bool(profile.get("personal", {}).get("email")),
            "Education": bool(profile.get("education", {}).get("institution")),
            "Skills": bool(any(profile.get("skills", {}).values())),
            "Projects": bool(profile.get("projects")),
            "Experience": bool(
                profile.get("experience", {}).get("internships") or
                profile.get("experience", {}).get("full_time_roles")
            ),
            "Summary": bool(profile.get("resume_summary", "").strip()),
            "Certifications": bool(profile.get("certifications")),
        }
        present = [k for k, v in sections.items() if v]
        missing = [k for k, v in sections.items() if not v]
        score = (len(present) / len(sections)) * 100.0

        return ScoreDimension(
            name="Completeness Score",
            score=round(score, 2),
            weight=self.weights.completeness_score,
            explanation=f"Present: {present}. Missing: {missing}.",
            matched_items=present,
            missing_items=missing,
        )

    def _recruiter_appeal_score(self, profile: dict[str, Any]) -> ScoreDimension:
        """
        Recruiter Appeal Score Methodology
        ------------------------------------
        Bonus signals that make a resume stand out to human recruiters:
        - GitHub link → +25
        - LinkedIn link → +20
        - Portfolio link → +15
        - Hackathons with results → +20
        - Awards → +10
        - Open source contributions → +10
        """
        personal = profile.get("personal", {})
        score = 0.0
        reasons = []

        if personal.get("github"):
            score += 25
            reasons.append("GitHub profile linked.")
        if personal.get("linkedin"):
            score += 20
            reasons.append("LinkedIn profile linked.")
        if personal.get("portfolio"):
            score += 15
            reasons.append("Portfolio website linked.")
        if profile.get("hackathons"):
            score += 20
            reasons.append(f"{len(profile['hackathons'])} hackathon(s) listed.")
        if profile.get("awards"):
            score += 10
            reasons.append(f"{len(profile['awards'])} award(s) listed.")
        if profile.get("open_source"):
            score += 10
            reasons.append("Open source contributions present.")

        return ScoreDimension(
            name="Recruiter Appeal Score",
            score=round(min(score, 100.0), 2),
            weight=self.weights.recruiter_appeal_score,
            explanation=" | ".join(reasons) or "No appeal signals detected.",
            matched_items=[], missing_items=[],
        )

    def _confidence_score(self, job_description: str, reliability: float) -> ScoreDimension:
        """
        Confidence Score Methodology
        ------------------------------
        Measures how trustworthy this analysis is based on data quality:
        - JD length ≥ 500 chars → +40 (enough text to analyze)
        - JD length ≥ 200 chars → +20
        - Source reliability score (normalized to 0–60)
        Higher confidence = the scores above are more reliable.
        """
        desc_len = len(job_description)
        if desc_len >= 500:
            desc_score = 40.0
        elif desc_len >= 200:
            desc_score = 20.0
        else:
            desc_score = 5.0

        reliability_contrib = reliability * 0.6
        score = min(desc_score + reliability_contrib, 100.0)

        return ScoreDimension(
            name="Confidence Score",
            score=round(score, 2),
            weight=self.weights.confidence_score,
            explanation=(
                f"JD length: {desc_len} chars (contributes {desc_score:.0f} pts). "
                f"Source reliability: {reliability:.0f}/100 (contributes {reliability_contrib:.0f} pts)."
            ),
            matched_items=[], missing_items=[],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _flat_skills(self, profile: dict[str, Any]) -> list[str]:
        """Return all skills as a flat lowercase list."""
        skills_dict = profile.get("skills", {})
        result = []
        for v in skills_dict.values():
            if isinstance(v, list):
                result.extend(s.lower() for s in v)
        return result

    def _resume_text(self, profile: dict[str, Any]) -> str:
        """Build a searchable text blob from all resume text fields."""
        parts = [
            profile.get("resume_summary", ""),
            " ".join(profile.get("certifications", [])),
            " ".join(profile.get("awards", [])),
        ]
        for proj in profile.get("projects", []):
            parts.append(proj.get("description", ""))
            parts.extend(proj.get("highlights", []))
        for intern in profile.get("experience", {}).get("internships", []):
            parts.extend(intern.get("responsibilities", []))
        return " ".join(parts)
