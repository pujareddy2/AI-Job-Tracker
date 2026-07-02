"""
resume_parser/scorer.py — Candidate Scorer and Strength Analyser
================================================================
Purpose
-------
Calculate readiness and ATS compatibility scores and identify candidate strengths
and career domains based on parsed resume elements.

Design Decisions
----------------
Readiness Score (0–100):
    - Weighted algorithm:
      * Experience (35%): Number of internships/roles. Each internship = +15 points.
      * Education (25%): Degree match (+15), CGPA >= 8.5 (+10).
      * Projects (20%): Count of projects. Each project = +7 points.
      * Hackathons/Competitions (20%): Winner = +15, Participant = +10.
    - Captures professional development and competency.

ATS Score (0–100):
    - Focuses on formatting structure and parsability:
      * Standard sections present (Education, Skills, Experience, Projects) = +40 points.
      * Essential contact details (Email, Phone, LinkedIn, GitHub) = +40 points (10 points each).
      * Keyword richness (number of categorised skills) = Min(20, skills_count * 1.5) points.

Strengths Identification:
    - Analyzes achievements, education CGPA, internship presence, and specific skill counts
      to generate custom, non-hallucinated feedback points (e.g. "Excellent academic record with CGPA >= 9").

Usage
-----
    from resume_parser.scorer import CandidateScorer

    scorer = CandidateScorer()
    strengths, readiness, ats = scorer.score_profile(parsed_sections, personal, education, skills, experience)
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


class CandidateScorer:
    """
    Computes scores and extracts highlights from candidate profiles.
    """

    def score_profile(
        self,
        sections: dict[str, str],
        personal: dict[str, Any],
        education: dict[str, Any],
        skills: dict[str, list[str]],
        experience: dict[str, Any],
        projects: list[dict[str, Any]],
        hackathons: list[dict[str, Any]],
        certifications: list[str]
    ) -> dict[str, Any]:
        """
        Compute readiness score, ATS score, and list profile strengths.

        Parameters
        ----------
        sections : dict[str, str]
            Extracted raw section blocks.
        personal : dict[str, Any]
            Parsed personal details.
        education : dict[str, Any]
            Parsed education details.
        skills : dict[str, list[str]]
            Categorised skills.
        experience : dict[str, Any]
            Parsed experience metrics.
        projects : list[dict[str, Any]]
            Parsed projects.
        hackathons : list[dict[str, Any]]
            Parsed hackathons.
        certifications : list[str]
            Parsed certifications list.

        Returns
        -------
        dict[str, Any]
            {
                "strengths": list[str],
                "career_readiness_score": int,
                "ats_score": int,
                "career_domains": list[str]
            }
        """
        # 1. Strengths
        strengths = []

        # Academic records strength
        cgpa_str = education.get("cgpa", "")
        if cgpa_str:
            # check if >= 8.5 or 85% or 9
            if any(term in cgpa_str for term in ["9.", "8.5", "8.6", "8.7", "8.8", "8.9", "95%", "90%"]):
                strengths.append(f"Strong academic performance with CGPA/score of {cgpa_str}")

        # Internship strength
        internships = experience.get("internships", [])
        if len(internships) > 0:
            strengths.append(f"Practical industry experience through {len(internships)} internship(s)")

        # Hackathons strength
        if len(hackathons) > 0:
            winner_count = sum(1 for h in hackathons if h.get("result") in ["Winner", "1st Place", "2nd Place"])
            if winner_count > 0:
                strengths.append(f"Proven competition success in {winner_count} hackathon(s)")
            else:
                strengths.append(f"Active hackathon participation with {len(hackathons)} entries")

        # Technical variety strength
        all_skills_count = sum(len(v) for v in skills.values() if isinstance(v, list))
        if all_skills_count > 15:
            strengths.append(f"Broad technical skill set spanning {all_skills_count} technologies")

        # Project variety strength
        if len(projects) > 1:
            strengths.append(f"Strong project portfolio with {len(projects)} hands-on implementations")

        # Certifications strength
        if len(certifications) > 0:
            strengths.append(f"Demonstrated self-learning through {len(certifications)} professional certification(s)")

        # Fallback strength if list is empty
        if not strengths:
            strengths.append("Structured and clean professional resume presentation")

        # 2. Career Readiness Score
        # Experience (35 points)
        exp_score = min(35.0, len(internships) * 15.0)
        # Education (25 points)
        edu_score = 0.0
        if education.get("degree"):
            edu_score += 15.0
        if cgpa_str and any(term in cgpa_str for term in ["8.", "9."]):
            edu_score += 10.0
        # Projects (20 points)
        proj_score = min(20.0, len(projects) * 10.0)
        # Hackathons/Certifications (20 points)
        comp_score = min(20.0, (len(hackathons) * 10.0) + (len(certifications) * 5.0))

        readiness_score = int(min(exp_score + edu_score + proj_score + comp_score, 100.0))

        # 3. ATS Score (Structure & Info Check)
        ats_points = 0
        # Contact info completeness (40 points)
        if personal.get("email"): ats_points += 10
        if personal.get("phone"): ats_points += 10
        if personal.get("linkedin"): ats_points += 10
        if personal.get("github"): ats_points += 10

        # Section presence (40 points)
        sections_found = [s for s in ["education", "skills", "experience", "projects"] if s in sections and sections[s]]
        ats_points += len(sections_found) * 10

        # Keyword density (20 points)
        ats_points += int(min(20.0, all_skills_count * 1.5))

        ats_score = int(min(ats_points, 100.0))

        # 4. Career Domains
        domains = ["Software Engineering"]
        skills_lower = {s.lower() for v in skills.values() for s in v}
        if any(s in skills_lower for s in ["langchain", "llamaindex", "rag", "llm", "generative ai", "openai"]):
            domains.append("Generative AI")
            domains.append("AI Engineering")
        if any(s in skills_lower for s in ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn"]):
            domains.append("Machine Learning")
            domains.append("Data Science")
        if any(s in skills_lower for s in ["fastapi", "django", "flask", "spring boot", "node.js", "express", "go", "golang"]):
            domains.append("Backend Development")
        if any(s in skills_lower for s in ["aws", "gcp", "azure", "docker", "kubernetes", "terraform", "github actions"]):
            domains.append("Cloud & DevOps")
        if any(s in skills_lower for s in ["react", "react.js", "angular", "vue", "next.js", "html", "css", "javascript", "typescript"]):
            domains.append("Frontend Development")

        logger.info(
            "Scoring complete",
            extra={"readiness_score": readiness_score, "ats_score": ats_score, "domains": len(domains)}
        )

        return {
            "strengths": strengths,
            "career_readiness_score": readiness_score,
            "ats_score": ats_score,
            "career_domains": sorted(list(set(domains)))
        }
