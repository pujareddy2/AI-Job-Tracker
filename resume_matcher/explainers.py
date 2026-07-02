"""
resume_matcher/explainers.py — Explainable Recommender and Tailoring Engine
==========================================================================
Purpose
-------
Generate explainable feedback reports, missing skills lists, and resume tailoring suggestions.
"""

from __future__ import annotations

from typing import Any

from job_model.universal_model import UniversalJobModel


class MatchExplainer:
    """
    Builds explainable recommendation reports.
    """

    def __init__(self, thresholds_config: dict[str, Any]) -> None:
        self.thresholds = thresholds_config.get(
            "match_thresholds",
            {
                "Excellent Match": 85,
                "Strong Match": 70,
                "Good Match": 55,
                "Potential Match": 40,
                "Needs Skill Improvement": 25,
                "Weak Match": 0
            }
        )

    def resolve_category(self, score: float) -> str:
        """Resolve match score to category string."""
        for cat, limit in sorted(self.thresholds.items(), key=lambda x: -x[1]):
            if score >= limit:
                return cat
        return "Weak Match"

    def compile_report(
        self,
        job: UniversalJobModel,
        profile: dict[str, Any],
        scores: dict[str, float]
    ) -> dict[str, Any]:
        """
        Generate detailed, explainable match feedback metrics.
        """
        overall = scores["overall"]
        category = self.resolve_category(overall)
        desc = job.job.job_description.lower()
        title = job.job.job_title.lower()

        # Matched and missing skills
        matched_skills = job.resume_match.resume_keywords_matched or []
        missing_skills = job.resume_match.resume_keywords_missing or []

        # Find relevant projects
        projects = profile.get("projects", [])
        relevant_projects = []
        for p in projects:
            p_techs = p.get("technologies", [])
            # Match if project uses keywords in desc
            matched_tech = [t for t in p_techs if t.lower() in desc]
            if matched_tech:
                relevant_projects.append(p.get("name") or "Unnamed Project")

        # Find relevant internships
        internships = profile.get("experience", {}).get("internships", [])
        relevant_internships = []
        for i in internships:
            i_techs = i.get("technologies", [])
            matched_tech = [t for t in i_techs if t.lower() in desc]
            if matched_tech:
                relevant_internships.append(f"{i.get('role')} at {i.get('company')}")

        # Relevant Certifications
        certs = profile.get("certifications", [])
        relevant_certs = [c for c in certs if c.lower() in desc]

        # Recommendation reasoning summary
        reason = (
            f"This job is categorized as an '{category}' with a score of {overall}%. "
            f"It aligns with your interest in {job.job.job_category} roles. "
        )
        if scores["eligibility"] >= 90:
            reason += "You satisfy the location and experience eligibility requirements. "
        if scores["technical"] >= 70:
            reason += f"Your profile demonstrates strong skill alignment, matching {len(matched_skills)} core technologies."

        # Compile strengths & weaknesses
        strengths = []
        if overall >= 70:
            strengths.append("High overall match score alignment")
        if scores["eligibility"] == 100:
            strengths.append("Meets location and fresher/entry eligibility requirements")
        if len(relevant_projects) > 0:
            strengths.append(f"Practical project experience: {', '.join(relevant_projects)}")
        if len(relevant_internships) > 0:
            strengths.append(f"Matching internship roles: {', '.join(relevant_internships)}")

        weaknesses = []
        if len(missing_skills) > 5:
            weaknesses.append(f"Missing {len(missing_skills)} preferred technology skills")
        if scores["career_fit"] < 60:
            weaknesses.append("Role type does not directly target your primary career goals")

        # Resume Tailoring suggestions
        tailoring = []
        if relevant_projects:
            tailoring.append(f"Feature your project '{relevant_projects[0]}' at the top of your Projects section.")
        if relevant_internships:
            tailoring.append(f"Emphasize the skills used during your internship: '{relevant_internships[0]}'.")
        if missing_skills:
            tailoring.append(f"Include references to missing skills like '{missing_skills[0]}' if you have basic familiarity.")

        # Skills to learn
        skills_to_learn = missing_skills[:5]

        return {
            "match_category": category,
            "overall_match_score": overall,
            "confidence_score": scores["confidence"],
            "recommendation_score": scores["recommendation"],
            "risk_score": scores["risk"],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "relevant_projects": relevant_projects,
            "relevant_internships": relevant_internships,
            "relevant_certifications": relevant_certs,
            "reason_for_recommendation": reason,
            "suggested_resume_improvements": tailoring,
            "suggested_skills_to_learn": skills_to_learn
        }
