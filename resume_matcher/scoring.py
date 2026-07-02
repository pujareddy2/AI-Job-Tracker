"""
resume_matcher/scoring.py — Multi-Level Score Calculator
=========================================================
Purpose
-------
Calculate multi-level scores (Eligibility, Technical, Career Fit, and Overall Match).
"""

from __future__ import annotations

from typing import Any

from job_model.universal_model import UniversalJobModel
from resume_matcher.semantic_intelligence import SemanticIntelligence


class ScoreCalculator:
    """
    Computes candidate-specific matching scores for job listings.
    """

    def __init__(self, rules_config: dict[str, Any]) -> None:
        self.config = rules_config
        self.weights = rules_config.get("weights", {"eligibility": 0.2, "technical": 0.5, "career_fit": 0.3})

    def calculate_eligibility(self, job: UniversalJobModel, profile: dict[str, Any]) -> float:
        """
        Calculate eligibility score (0-100) based on location, experience, and batch.
        """
        el_weights = self.config.get("eligibility_weights", {"location": 0.3, "experience": 0.3, "graduation": 0.4})
        
        # 1. Location Match
        loc_score = 0.0
        preferred_locs = profile.get("candidate_analysis", {}).get("preferred_locations", [])
        city = str(job.location.city).lower()
        if job.location.remote:
            loc_score = 100.0
        elif any(loc.lower() in city for loc in preferred_locs):
            loc_score = 100.0
        elif job.location.country == "India":
            loc_score = 70.0  # general India offset

        # 2. Experience Match
        exp_score = 100.0
        min_exp = job.job.minimum_experience
        if min_exp is not None and min_exp > 1:
            exp_score = 0.0  # candidate is fresher/2027 grad

        # 3. Graduation Batch Match
        grad_score = 0.0
        grad_year = profile.get("education", {}).get("graduation_year", 2027)
        desc = job.job.job_description.lower()
        if str(grad_year) in desc or "2027" in desc or "campus" in desc or "fresher" in desc:
            grad_score = 100.0
        elif not job.job.minimum_experience:
            grad_score = 70.0  # default entry-level fallback

        # Weighted calculation
        score = (
            loc_score * el_weights.get("location", 0.3) +
            exp_score * el_weights.get("experience", 0.3) +
            grad_score * el_weights.get("graduation", 0.4)
        )
        return round(score, 2)

    def calculate_technical(self, job: UniversalJobModel, profile: dict[str, Any]) -> float:
        """
        Calculate technical score (0-100) based on skills, projects, and internships.
        """
        tech_weights = self.config.get("technical_weights", {"skills": 0.4, "projects": 0.3, "internships": 0.2, "certifications": 0.1})
        desc = job.job.job_description.lower()
        title = job.job.job_title.lower()

        # 1. Skills Matching
        skills_score = 0.0
        flat_skills = []
        skills_dict = profile.get("skills", {})
        for cat, items in skills_dict.items():
            if isinstance(items, list):
                flat_skills.extend(items)
        
        matched_skills = []
        missing_skills = []
        for skill in flat_skills:
            if SemanticIntelligence.check_match(skill, desc) or SemanticIntelligence.check_match(skill, title):
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        job.resume_match.resume_keywords_matched = matched_skills
        job.resume_match.resume_keywords_missing = missing_skills

        if flat_skills:
            skills_score = (len(matched_skills) / len(flat_skills)) * 100.0
        
        # 2. Projects Matching
        projects_score = 0.0
        projects = profile.get("projects", [])
        matched_projects = 0
        for proj in projects:
            proj_techs = proj.get("technologies", [])
            # If any project tech matches the job desc
            if any(SemanticIntelligence.check_match(tech, desc) for tech in proj_techs):
                matched_projects += 1
        
        if projects:
            projects_score = (matched_projects / len(projects)) * 100.0

        # 3. Internship Matching
        internships_score = 0.0
        internships = profile.get("experience", {}).get("internships", [])
        matched_internships = 0
        for intern in internships:
            intern_techs = intern.get("technologies", [])
            if any(SemanticIntelligence.check_match(tech, desc) for tech in intern_techs):
                matched_internships += 1
        
        if internships:
            internships_score = (matched_internships / len(internships)) * 100.0
        else:
            internships_score = 50.0  # baseline if no internships but have projects

        # 4. Certifications
        certs_score = 0.0
        certs = profile.get("certifications", [])
        if certs:
            matched_certs = [c for c in certs if c.lower() in desc]
            certs_score = 100.0 if matched_certs else 50.0

        # Weighted calculation
        score = (
            skills_score * tech_weights.get("skills", 0.4) +
            projects_score * tech_weights.get("projects", 0.3) +
            internships_score * tech_weights.get("internships", 0.2) +
            certs_score * tech_weights.get("certifications", 0.1)
        )
        return round(score, 2)

    def calculate_career_fit(self, job: UniversalJobModel, profile: dict[str, Any]) -> float:
        """
        Calculate career fit score (0-100) based on roles, domains, and goals.
        """
        fit_weights = self.config.get("career_fit_weights", {"role": 0.4, "domain": 0.3, "goals": 0.3})
        title = job.job.job_title.lower()
        desc = job.job.job_description.lower()

        # 1. Role Match
        role_score = 0.0
        preferred_roles = profile.get("candidate_analysis", {}).get("preferred_roles", [])
        for role in preferred_roles:
            if role.lower() in title:
                role_score = 100.0
                break
        if not role_score:
            # Check related terms
            if any(term in title for term in ["ai", "llm", "rag", "ml", "nlp", "backend"]):
                role_score = 70.0

        # 2. Domain Match
        domain_score = 0.0
        preferred_domains = profile.get("candidate_analysis", {}).get("career_domains", [])
        for domain in preferred_domains:
            if domain.lower() in desc or domain.lower() in title:
                domain_score = 100.0
                break
        if not domain_score:
            domain_score = 50.0  # baseline

        # 3. Career Goals Match
        goals_score = 50.0
        career_goals = profile.get("candidate_analysis", {}).get("preferred_industries", [])
        matched_goals = [goal for goal in career_goals if goal.lower() in desc]
        if matched_goals:
            goals_score = 100.0

        # Weighted calculation
        score = (
            role_score * fit_weights.get("role", 0.4) +
            domain_score * fit_weights.get("domain", 0.3) +
            goals_score * fit_weights.get("goals", 0.3)
        )
        return round(score, 2)

    def calculate_scores(self, job: UniversalJobModel, profile: dict[str, Any]) -> dict[str, float]:
        """Calculate eligibility, technical, career fit, and aggregated overall match score."""
        eligibility = self.calculate_eligibility(job, profile)
        technical = self.calculate_technical(job, profile)
        career_fit = self.calculate_career_fit(job, profile)

        # Aggregate weighted score
        overall = (
            eligibility * self.weights.get("eligibility", 0.2) +
            technical * self.weights.get("technical", 0.5) +
            career_fit * self.weights.get("career_fit", 0.3)
        )

        # Calculate Confidence Score (based on source trust and description length)
        trust = job.reliability.reliability_score
        desc_len_bonus = min(20, len(job.job.job_description) / 100)
        confidence = min(100.0, trust * 0.8 + desc_len_bonus)

        # Recommendation score = overall match scaled by confidence
        recommendation = round((overall * 0.7 + confidence * 0.3), 2)

        # Risk Score (increases if reliability is poor or matches are low)
        risk = round(max(0.0, 100.0 - overall), 2)

        return {
            "eligibility": eligibility,
            "technical": technical,
            "career_fit": career_fit,
            "overall": round(overall, 2),
            "confidence": round(confidence, 2),
            "recommendation": recommendation,
            "risk": risk
        }
