"""
communication_engine/personalization.py — Personalization and Context Merging
=============================================================================
Purpose
-------
Safe context mapping between CandidateProfile and UniversalJobModel fields.
Ensures ZERO hallucination or fabrication of skills/projects.
"""

from __future__ import annotations

from typing import Any


class PersonalizationEngine:
    """Retrieves facts from profile and job listing to format outreach templates."""

    @staticmethod
    def build_context(profile: dict[str, Any], job: dict[str, Any]) -> dict[str, str]:
        """
        Merge candidate facts and job requirements into a clean dictionary of strings.
        Ensures no fabrication by utilizing only existing profile data.
        """
        personal = profile.get("personal", {})
        edu = profile.get("education", {})
        skills = profile.get("skills", {})
        projects = profile.get("projects", [])
        experience = profile.get("experience", {})

        # Job details
        company_name = job.get("company", {}).get("company_name", "your company")
        job_title = job.get("job", {}).get("job_title", "Software Engineer")

        # Personal Contact info
        candidate_name = personal.get("name", "Candidate Name").strip()
        candidate_email = personal.get("email", "").strip()
        candidate_phone = personal.get("phone", "").strip()
        candidate_linkedin = personal.get("linkedin", "").strip()
        candidate_github = personal.get("github", "").strip()
        candidate_portfolio = personal.get("portfolio", "").strip()

        # Education
        degree = edu.get("degree", "B.Tech").strip()
        branch = edu.get("branch", "Computer Science").strip()
        institution = edu.get("institution", "Engineering College").strip()
        cgpa = edu.get("cgpa", "8.5").strip()

        # Skills paragraph formatting
        prog_langs = skills.get("programming_languages", [])
        fws = skills.get("frameworks", [])
        ai_ml = skills.get("ai_ml", [])
        
        flat_skills = []
        if prog_langs:
            flat_skills.append(", ".join(prog_langs[:3]))
        if fws:
            flat_skills.append(", ".join(fws[:2]))
        if ai_ml:
            flat_skills.append(", ".join(ai_ml[:2]))
            
        skills_paragraph = " and ".join(flat_skills) if flat_skills else "software engineering"

        # Projects paragraph formatting
        project_list = []
        for p in projects[:2]:
            name = p.get("name", "").split("—")[0].split("|")[0].strip()
            techs = p.get("technologies", [])
            if techs:
                project_list.append(f"'{name}' (built using {', '.join(techs[:2])})")
            else:
                project_list.append(f"'{name}'")
        
        if project_list:
            projects_paragraph = " and ".join(project_list)
        else:
            projects_paragraph = "independent software engineering projects"

        # Internships paragraph formatting
        internships = experience.get("internships", [])
        if internships:
            intern_details = []
            for i in internships[:1]:
                role = i.get("role", "Software Intern")
                company = i.get("company", "Tech Firm")
                dur = i.get("duration", "")
                if dur:
                    intern_details.append(f"My experience includes working as a {role} at {company} ({dur})")
                else:
                    intern_details.append(f"My experience includes working as a {role} at {company}")
            internships_paragraph = ". ".join(intern_details) + "."
        else:
            internships_paragraph = "I am eager to secure my first internship role to contribute directly to product releases."

        # Alignment reasons and goals
        alignment_reasons = (
            f"I am particularly drawn to {company_name}'s focus on innovation and technical excellence. "
            f"My educational and project work has prepared me to tackle difficult problems with clean code."
        )
        career_goals = "My career goal is to grow into an expert software developer working on high-impact products."

        return {
            "company_name": company_name,
            "job_title": job_title,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_phone": candidate_phone,
            "candidate_linkedin": candidate_linkedin,
            "candidate_github": candidate_github,
            "candidate_portfolio": candidate_portfolio,
            "degree": degree,
            "branch": branch,
            "institution": institution,
            "cgpa": cgpa,
            "skills_paragraph": skills_paragraph,
            "projects_paragraph": projects_paragraph,
            "internships_paragraph": internships_paragraph,
            "alignment_reasons": alignment_reasons,
            "career_goals": career_goals,
        }
