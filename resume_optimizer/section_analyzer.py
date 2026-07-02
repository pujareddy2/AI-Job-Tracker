"""
resume_optimizer/section_analyzer.py — Resume Section-by-Section Analyzer
==========================================================================
Purpose
-------
Evaluate every section of the candidate's resume against the job description
and produce specific, actionable improvement suggestions.

Design Philosophy
-----------------
- Suggestions are personalized: they reference actual profile content,
  not generic advice.
- Never invent content: suggestions only propose reorganization, emphasis,
  or elaboration of EXISTING content.
- Suggestions are ordered by impact (highest impact first).
- Every section has defined quality criteria with binary/graded checks.
"""

from __future__ import annotations

import re
from typing import Any

from resume_optimizer.config import OptimizerConfig
from resume_optimizer.models import (
    ProjectAnalysis,
    InternshipAnalysis,
    CertificationAnalysis,
    ResumeSectionsAnalysis,
    SectionReport,
)


def _mentions_any(text: str, items: list[str]) -> bool:
    """Check if any item from a list appears in the text (case-insensitive)."""
    text_lower = text.lower()
    return any(item.lower() in text_lower for item in items if item)


class SectionAnalyzer:
    """
    Evaluates every resume section and generates improvement suggestions.

    Parameters
    ----------
    config : OptimizerConfig
        Engine configuration.

    Usage
    -----
        analyzer = SectionAnalyzer(config)
        result = analyzer.analyze(profile, job_id, job_description, tech_stack)
    """

    def __init__(self, config: OptimizerConfig) -> None:
        self.config = config

    def analyze(
        self,
        profile: dict[str, Any],
        job_id: str,
        job_description: str,
        job_tech_stack: list[str],
        job_required_skills: list[str],
    ) -> ResumeSectionsAnalysis:
        """
        Analyze all resume sections against the job.

        Returns
        -------
        ResumeSectionsAnalysis
            Complete section analysis with scores and suggestions.
        """
        jd = job_description.lower()
        stack = [t.lower() for t in job_tech_stack]

        header = self._analyze_header(profile)
        summary = self._analyze_summary(profile, jd)
        education = self._analyze_education(profile, jd)
        projects = self._analyze_projects_section(profile, jd, stack)
        internships = self._analyze_internships_section(profile, jd, stack)
        skills = self._analyze_skills_section(profile, jd, stack, job_required_skills)
        certifications = self._analyze_certifications_section(profile, jd)
        hackathons = self._analyze_hackathons_section(profile, jd)
        awards = self._analyze_awards_section(profile, jd)

        # Weighted average
        weights = self.config.section_weights
        overall = (
            header.score * weights.header +
            summary.score * weights.summary +
            education.score * weights.education +
            projects.score * weights.projects +
            internships.score * weights.internships +
            skills.score * weights.skills +
            certifications.score * weights.certifications +
            hackathons.score * weights.hackathons +
            awards.score * weights.awards
        )

        return ResumeSectionsAnalysis(
            job_id=job_id,
            header=header,
            summary=summary,
            education=education,
            projects=projects,
            internships=internships,
            skills=skills,
            certifications=certifications,
            hackathons=hackathons,
            awards=awards,
            overall_section_score=round(min(overall, 100.0), 2),
        )

    # ------------------------------------------------------------------
    # Section analyzers
    # ------------------------------------------------------------------

    def _analyze_header(self, profile: dict[str, Any]) -> SectionReport:
        """
        Header Section Analysis
        -----------------------
        Checks: Name, Email, Phone, LinkedIn, GitHub, Portfolio.
        Each present element contributes to the score.
        Missing critical links (GitHub, LinkedIn) are flagged as high-impact.
        """
        personal = profile.get("personal", {})
        strengths, weaknesses, suggestions = [], [], []
        score = 0.0

        if personal.get("name"):
            score += 20
            strengths.append("Full name present.")
        else:
            weaknesses.append("Name missing.")
            suggestions.append("Add your full name to the resume header.")

        if personal.get("email"):
            score += 20
            strengths.append("Email address present.")
        else:
            weaknesses.append("Email missing.")
            suggestions.append("Add a professional email address to the header.")

        if personal.get("phone"):
            score += 15
            strengths.append("Phone number present.")
        else:
            weaknesses.append("Phone missing.")
            suggestions.append("Add your phone number.")

        if personal.get("linkedin"):
            score += 20
            strengths.append("LinkedIn profile linked.")
        else:
            weaknesses.append("LinkedIn URL missing.")
            suggestions.append("Add your LinkedIn profile URL — recruiters routinely click it.")

        if personal.get("github"):
            score += 20
            strengths.append("GitHub profile linked.")
        else:
            weaknesses.append("GitHub URL missing.")
            suggestions.append("Add your GitHub profile URL — critical for technical roles.")

        if personal.get("portfolio"):
            score += 5
            strengths.append("Portfolio linked.")

        return SectionReport(
            section_name="Header",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_summary(self, profile: dict[str, Any], jd_text: str) -> SectionReport:
        """
        Summary Section Analysis
        ------------------------
        Checks: presence, length (50–200 words), keyword coverage, specificity.
        A strong summary is concise, role-specific, and uses JD-matched keywords.
        """
        summary = profile.get("resume_summary", "").strip()
        strengths, weaknesses, suggestions = [], [], []

        if not summary:
            return SectionReport(
                section_name="Summary",
                present=False,
                score=0.0,
                strengths=[],
                weaknesses=["Summary section is completely missing."],
                suggestions=[
                    "Add a 3–5 sentence professional summary at the top of your resume. "
                    "Include your field (AI/ML/Backend), key skills, and a notable achievement."
                ],
            )

        word_count = len(summary.split())
        score = 0.0

        if word_count >= 50:
            score += 30
            strengths.append(f"Summary has {word_count} words — adequate length.")
        elif word_count >= 20:
            score += 15
            weaknesses.append(f"Summary is short ({word_count} words). Aim for 50–100 words.")
            suggestions.append("Expand the summary to 50–100 words. Mention your top 3 skills and a measurable achievement.")
        else:
            weaknesses.append(f"Summary is too brief ({word_count} words).")
            suggestions.append("Rewrite the summary — it's too short. Include your role, top skills, and one achievement.")

        # Keyword coverage in summary
        skills_flat = []
        for v in profile.get("skills", {}).values():
            if isinstance(v, list):
                skills_flat.extend(v)

        summary_lower = summary.lower()
        matched_skills = [s for s in skills_flat if s.lower() in summary_lower]
        if len(matched_skills) >= 3:
            score += 40
            strengths.append(f"Summary mentions {len(matched_skills)} key skills.")
        elif matched_skills:
            score += 20
            weaknesses.append("Summary mentions few key skills.")
            suggestions.append(f"Mention more of your core skills in the summary (e.g., {', '.join(skills_flat[:3])}).")
        else:
            weaknesses.append("Summary does not mention any key skills.")
            suggestions.append("Start the summary with your top technical skills.")

        # JD keyword overlap
        jd_words = set(jd_text.split())
        summary_words = set(summary_lower.split())
        overlap = jd_words & summary_words
        if len(overlap) >= 5:
            score += 30
            strengths.append("Summary aligns well with JD keywords.")
        else:
            weaknesses.append("Summary has low overlap with JD keywords.")
            suggestions.append("Tailor the summary to include more keywords from the job description.")

        return SectionReport(
            section_name="Summary",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_education(self, profile: dict[str, Any], jd_text: str) -> SectionReport:
        """
        Education Section Analysis
        --------------------------
        Checks: degree presence, CGPA, expected graduation, institution name.
        """
        edu = profile.get("education", {})
        strengths, weaknesses, suggestions = [], [], []
        score = 0.0

        if edu.get("institution"):
            score += 25
            strengths.append(f"Institution: {edu['institution'][:40]}.")
        else:
            weaknesses.append("Institution name not present.")
            suggestions.append("Ensure institution name is fully written on your resume.")

        cgpa_str = edu.get("cgpa", "")
        if cgpa_str:
            try:
                cgpa = float(cgpa_str.split("/")[0])
                if cgpa >= 8.5:
                    score += 35
                    strengths.append(f"Strong CGPA: {cgpa_str} — above most shortlisting thresholds.")
                elif cgpa >= 7.5:
                    score += 25
                    strengths.append(f"Good CGPA: {cgpa_str}.")
                else:
                    score += 10
                    weaknesses.append(f"CGPA {cgpa_str} may be below some company thresholds (usually 7.5+).")
                    suggestions.append("If CGPA is below 7.5, consider highlighting subject-specific or semester GPA.")
            except (ValueError, IndexError):
                weaknesses.append("CGPA format not recognized.")
                suggestions.append("Format CGPA as 'X.X/10' or 'X.X/4' for clarity.")
        else:
            weaknesses.append("CGPA not found in profile.")
            suggestions.append("Add your CGPA to the education section.")

        grad_year = edu.get("graduation_year")
        if grad_year:
            score += 20
            strengths.append(f"Graduation year: {grad_year}.")
            if edu.get("expected"):
                strengths.append("Clearly marked as expected graduation.")
        else:
            weaknesses.append("Graduation year not specified.")
            suggestions.append("Add your expected or actual graduation year.")

        if edu.get("degree") or edu.get("branch"):
            score += 20
            strengths.append(f"Degree/branch specified: {edu.get('degree','')} {edu.get('branch','')}.")
        else:
            weaknesses.append("Degree or branch not extracted.")
            suggestions.append("Ensure degree and branch/specialization are clearly stated.")

        return SectionReport(
            section_name="Education",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_projects_section(
        self, profile: dict[str, Any], jd_text: str, stack: list[str]
    ) -> SectionReport:
        """
        Projects Section Analysis
        -------------------------
        Checks: count, descriptions, technology tags, quantified impact.
        """
        projects = profile.get("projects", [])
        strengths, weaknesses, suggestions = [], [], []

        if not projects:
            return SectionReport(
                section_name="Projects",
                present=False,
                score=0.0,
                weaknesses=["No projects found in profile."],
                suggestions=["Add at least 2–3 personal or academic projects with technology tags and descriptions."],
            )

        score = 0.0
        score += min(len(projects) * 10, 30)
        if len(projects) >= 3:
            strengths.append(f"{len(projects)} projects listed — good volume.")
        else:
            weaknesses.append(f"Only {len(projects)} project(s). Aim for 3–4.")
            suggestions.append("Add more projects to reach 3–4 total.")

        # Projects with descriptions
        with_desc = [p for p in projects if p.get("description") and len(p["description"]) > 30]
        if len(with_desc) == len(projects):
            score += 25
            strengths.append("All projects have descriptions.")
        elif with_desc:
            score += 15
            weaknesses.append(f"{len(projects) - len(with_desc)} project(s) lack descriptions.")
            suggestions.append("Add a 2–3 sentence description to every project explaining the problem, solution, and impact.")
        else:
            weaknesses.append("No projects have descriptions.")
            suggestions.append("Add descriptions to all projects — this is the most impactful resume improvement.")

        # Projects with tech tags
        with_tech = [p for p in projects if p.get("technologies")]
        if len(with_tech) == len(projects):
            score += 20
            strengths.append("All projects have technology tags.")
        else:
            weaknesses.append(f"{len(projects) - len(with_tech)} project(s) missing technology tags.")
            suggestions.append("Add technology tags to every project (e.g., Python, FastAPI, PostgreSQL).")

        # Relevant projects (tech overlap with JD)
        relevant = [
            p for p in projects
            if any(t.lower() in jd_text for t in p.get("technologies", []))
            or any(t in p.get("description", "").lower() for t in stack)
        ]
        if relevant:
            score += 25
            strengths.append(f"{len(relevant)} project(s) directly relevant to this job.")
            best = relevant[0]
            suggestions.append(
                f"Move '{best.get('name', 'your most relevant project')}' to the top of the projects section "
                f"— it has the strongest technology overlap with this role."
            )
        else:
            weaknesses.append("No projects have strong technology overlap with this JD.")
            suggestions.append(
                f"Emphasize any existing project that uses {', '.join(stack[:3]) if stack else 'relevant technologies'}."
            )

        return SectionReport(
            section_name="Projects",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_internships_section(
        self, profile: dict[str, Any], jd_text: str, stack: list[str]
    ) -> SectionReport:
        """
        Internships Section Analysis
        ----------------------------
        Checks: presence, role clarity, technology match, responsibilities.
        """
        internships = profile.get("experience", {}).get("internships", [])
        strengths, weaknesses, suggestions = [], [], []

        if not internships:
            return SectionReport(
                section_name="Internships",
                present=False,
                score=40.0,  # Fresher baseline — not penalized heavily
                weaknesses=["No internship experience found in profile."],
                suggestions=[
                    "Apply to internships to strengthen your profile. "
                    "Virtual internships and open-source contributions also count.",
                    "Highlight any freelance work, college research, or teaching assistant experience."
                ],
            )

        score = min(len(internships) * 25, 50)
        strengths.append(f"{len(internships)} internship(s) listed.")

        with_tech = [i for i in internships if i.get("technologies")]
        with_resp = [i for i in internships if i.get("responsibilities")]

        if with_tech:
            score += 25
            strengths.append("Technologies listed in internship(s).")
        else:
            weaknesses.append("Internship(s) missing technology tags.")
            suggestions.append("Add the technologies you used in each internship (e.g., Python, FastAPI, MySQL).")

        if with_resp:
            score += 25
            strengths.append("Responsibilities listed for internship(s).")
        else:
            weaknesses.append("No responsibilities/achievements listed.")
            suggestions.append("Add 2–3 bullet points per internship describing what you built and its impact.")

        # Tech match
        matched = [
            i for i in internships
            if any(t.lower() in jd_text for t in i.get("technologies", []))
        ]
        if matched:
            strengths.append(f"Internship at '{matched[0].get('company','')}' has tech overlap with JD.")
            suggestions.append(
                f"Highlight your role at '{matched[0].get('company','')}' more prominently — "
                "it matches this job's technology stack."
            )

        return SectionReport(
            section_name="Internships",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_skills_section(
        self,
        profile: dict[str, Any],
        jd_text: str,
        stack: list[str],
        required_skills: list[str],
    ) -> SectionReport:
        """
        Skills Section Analysis
        -----------------------
        Checks: categorization, coverage, ordering, missing critical skills.
        """
        skills = profile.get("skills", {})
        strengths, weaknesses, suggestions = [], [], []
        score = 0.0

        flat_skills = []
        for v in skills.values():
            if isinstance(v, list):
                flat_skills.extend(v)

        if not flat_skills:
            return SectionReport(
                section_name="Skills",
                present=False,
                score=0.0,
                weaknesses=["No skills found in profile."],
                suggestions=["Add a comprehensive skills section organized by category."],
            )

        # Categorization check
        non_empty_cats = [k for k, v in skills.items() if isinstance(v, list) and v and k != "languages_spoken"]
        if len(non_empty_cats) >= 3:
            score += 30
            strengths.append(f"Skills organized into {len(non_empty_cats)} categories.")
        else:
            weaknesses.append("Skills are not well-categorized.")
            suggestions.append("Organize skills into categories: Languages, Frameworks, Databases, AI/ML, Cloud, Tools.")

        # Coverage of JD stack
        flat_lower = {s.lower() for s in flat_skills}
        matched_stack = [t for t in stack if any(t in s or s in t for s in flat_lower)]
        if matched_stack:
            score += 40
            strengths.append(f"Covers {len(matched_stack)} of {len(stack)} JD tech stack items.")
        else:
            weaknesses.append("Skills section has low overlap with JD tech stack.")
            missing_critical = [t for t in (required_skills or stack) if t.lower() not in flat_lower][:5]
            if missing_critical:
                suggestions.append(
                    f"The following JD skills are missing from your resume: {', '.join(missing_critical)}. "
                    "Only add them if you actually have experience with them."
                )

        # Total skill count
        if len(flat_skills) >= 10:
            score += 30
            strengths.append(f"Strong skill inventory: {len(flat_skills)} skills listed.")
        elif len(flat_skills) >= 5:
            score += 15
            weaknesses.append(f"Only {len(flat_skills)} skills listed. Aim for 10+.")
            suggestions.append("List all tools, libraries, and platforms you have used.")

        return SectionReport(
            section_name="Skills",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_certifications_section(
        self, profile: dict[str, Any], jd_text: str
    ) -> SectionReport:
        """
        Certifications Section Analysis
        --------------------------------
        Checks: presence, relevance to JD, ordering recommendation.
        """
        certs = profile.get("certifications", [])
        strengths, weaknesses, suggestions = [], [], []

        if not certs:
            cert_keywords = ["certification", "certified", "aws", "coursera", "google cloud"]
            if any(kw in jd_text for kw in cert_keywords):
                return SectionReport(
                    section_name="Certifications",
                    present=False,
                    score=20.0,
                    weaknesses=["No certifications found. JD appears to value certifications."],
                    suggestions=[
                        "Pursue relevant certifications to strengthen your profile for this role. "
                        "Free options: Google ML Crash Course, AWS Cloud Practitioner (free tier), NPTEL courses."
                    ],
                )
            return SectionReport(
                section_name="Certifications",
                present=False,
                score=60.0,  # neutral — JD doesn't require them
                strengths=["JD does not explicitly require certifications."],
                weaknesses=[],
                suggestions=["Add any completed online courses or certifications to boost your profile."],
            )

        score = min(len(certs) * 20, 60)
        strengths.append(f"{len(certs)} certification(s) listed.")

        relevant = [c for c in certs if any(w in jd_text for w in c.lower().split())]
        if relevant:
            score += 40
            strengths.append(f"Relevant certifications: {', '.join(relevant)}.")
            suggestions.append(f"Move '{relevant[0]}' to the top of the certifications section — it's directly relevant.")
        else:
            weaknesses.append("Listed certifications are not directly mentioned in the JD.")
            suggestions.append("Consider obtaining a certification more relevant to this specific role.")

        return SectionReport(
            section_name="Certifications",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _analyze_hackathons_section(
        self, profile: dict[str, Any], jd_text: str
    ) -> SectionReport:
        hackathons = profile.get("hackathons", [])
        if not hackathons:
            return SectionReport(
                section_name="Hackathons",
                present=False,
                score=50.0,
                strengths=["Not required for this role."],
                suggestions=["Participating in hackathons strengthens your profile and provides project material."],
            )

        with_results = [h for h in hackathons if h.get("result")]
        score = 60.0 + (len(hackathons) * 10) + (len(with_results) * 10)
        strengths = [f"{len(hackathons)} hackathon(s) listed."]
        suggestions = []
        if with_results:
            strengths.append(f"{len(with_results)} hackathon(s) with placement/result.")
            suggestions.append(f"Emphasize '{with_results[0].get('result','')}' result at '{with_results[0].get('name','')}' — it's a strong signal.")

        return SectionReport(
            section_name="Hackathons",
            present=True,
            score=round(min(score, 100.0), 2),
            strengths=strengths,
            weaknesses=[],
            suggestions=suggestions,
        )

    def _analyze_awards_section(self, profile: dict[str, Any], jd_text: str) -> SectionReport:
        awards = profile.get("awards", [])
        if not awards:
            return SectionReport(
                section_name="Awards",
                present=False,
                score=60.0,
                strengths=["Awards section not required for this role."],
                suggestions=["Add any academic awards, scholarships, or recognition to strengthen recruiter appeal."],
            )

        return SectionReport(
            section_name="Awards",
            present=True,
            score=80.0,
            strengths=[f"{len(awards)} award(s) listed — positive recruiter signal."],
            weaknesses=[],
            suggestions=[],
        )

    # ------------------------------------------------------------------
    # Per-item analyzers (used by the engine directly)
    # ------------------------------------------------------------------

    def analyze_projects(
        self,
        profile: dict[str, Any],
        job_description: str,
        job_tech_stack: list[str],
    ) -> list[ProjectAnalysis]:
        """
        Generate a ProjectAnalysis for every project in the profile.
        Provides per-project ordering and highlight recommendations.
        """
        projects = profile.get("projects", [])
        jd = job_description.lower()
        stack = {t.lower() for t in job_tech_stack}
        results = []

        for proj in projects:
            techs = [t.lower() for t in proj.get("technologies", [])]
            desc = proj.get("description", "").lower()

            # Technology match
            matched_techs = [t for t in techs if t in stack or t in jd]
            missing_techs = list(stack - set(techs))[:5]
            tech_match = (len(matched_techs) / max(len(techs), 1)) * 100.0

            # Industry match (simple domain signal)
            domain_signals = ["ai", "ml", "backend", "api", "database", "cloud", "web", "nlp", "rag"]
            industry_hits = sum(1 for s in domain_signals if s in jd and s in desc)
            industry_match = min(industry_hits * 20, 100.0)

            # Role match
            role_signals = ["engineer", "developer", "analyst", "scientist", "architect"]
            role_match = 70.0 if any(s in jd for s in role_signals) else 40.0

            relevance = round((tech_match * 0.6 + industry_match * 0.25 + role_match * 0.15), 2)

            # Recommendation
            if relevance >= 70:
                rec, reason = "Move Up", f"High relevance ({relevance:.0f}/100) — should be near top of projects."
            elif relevance >= 40:
                rec, reason = "Highlight", f"Moderate relevance ({relevance:.0f}/100) — add more context."
            elif len(desc) < 50:
                rec, reason = "Expand", "Description is too brief to demonstrate impact."
            else:
                rec, reason = "Keep", f"Low relevance to this specific job ({relevance:.0f}/100)."

            results.append(ProjectAnalysis(
                project_name=proj.get("name", "Unnamed"),
                relevance_score=relevance,
                technology_match=round(tech_match, 2),
                industry_match=round(industry_match, 2),
                role_match=role_match,
                recommendation=rec,
                reason=reason,
                matched_technologies=matched_techs,
                missing_technologies=missing_techs,
            ))

        # Sort by relevance descending
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    def analyze_internships(
        self,
        profile: dict[str, Any],
        job_description: str,
        job_tech_stack: list[str],
    ) -> list[InternshipAnalysis]:
        """Generate an InternshipAnalysis for every internship in the profile."""
        internships = profile.get("experience", {}).get("internships", [])
        jd = job_description.lower()
        stack = {t.lower() for t in job_tech_stack}
        results = []

        for intern in internships:
            techs = [t.lower() for t in intern.get("technologies", [])]
            matched = [t for t in techs if t in stack or t in jd]
            relevance = (len(matched) / max(len(techs), 1)) * 100.0

            suggestions = []
            if not intern.get("responsibilities"):
                suggestions.append("Add bullet-point responsibilities describing what you built.")
            if not techs:
                suggestions.append("List the technologies you used during this internship.")
            if matched:
                suggestions.append(
                    f"Emphasize {', '.join(matched[:3])} in your description — they match this JD."
                )

            results.append(InternshipAnalysis(
                role=intern.get("role", ""),
                company=intern.get("company", ""),
                relevance_score=round(relevance, 2),
                suggestions=suggestions,
                recommendation="Highlight" if relevance >= 50 else "Add Details",
                reason=f"Technology match: {len(matched)}/{len(techs)} items match JD stack.",
            ))

        return results

    def analyze_certifications(
        self,
        profile: dict[str, Any],
        job_description: str,
    ) -> list[CertificationAnalysis]:
        """Generate a CertificationAnalysis for every certification."""
        certs = profile.get("certifications", [])
        jd = job_description.lower()
        results = []

        for cert in certs:
            cert_lower = cert.lower()
            words = cert_lower.split()
            relevance = 100.0 if any(w in jd for w in words if len(w) > 3) else 40.0

            results.append(CertificationAnalysis(
                certification_name=cert,
                relevance_score=relevance,
                recommendation="Highlight" if relevance >= 70 else "Keep",
                reason=(
                    "Directly mentioned or closely related to JD requirements."
                    if relevance >= 70
                    else "Not directly referenced in this JD — still adds general credibility."
                ),
            ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results
