"""
resume_optimizer/engine.py — Resume Optimization Engine Orchestrator
=====================================================================
Purpose
-------
The main orchestrator that wires ATSScorer, KeywordOptimizer, SectionAnalyzer,
and GapAnalyzer together to produce complete per-job optimization reports
and an aggregated career summary.

Design Philosophy
-----------------
- Never re-reads the resume PDF. Uses only the CandidateProfile from cache.
- Per-job reports are independent — no shared state between jobs.
- Failures are non-fatal: if one job fails, the rest continue.
- Reports are JSON-serialised to cache/resume_reports/ for persistence.
- The engine is designed for future multi-resume version support.

Integration Points
------------------
- Called by scheduler/pipeline.py in Stage 6.5 (after matching).
- Called by scripts/resume_optimizer_cli.py for manual runs.
- Top suggestions are passed to the email notification engine.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings, PROJECT_ROOT
from resume_optimizer.ats_scorer import ATSScorer
from resume_optimizer.config import DEFAULT_CONFIG, OptimizerConfig
from resume_optimizer.gap_analyzer import GapAnalyzer
from resume_optimizer.keyword_optimizer import KeywordOptimizer
from resume_optimizer.models import (
    CareerSummaryReport,
    ImprovementScoreCard,
    PerJobOptimizationReport,
    ResumeSuggestion,
    ResumeVersionRecommendation,
)
from resume_optimizer.section_analyzer import SectionAnalyzer
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeOptimizationEngine:
    """
    Master orchestrator for the AI Resume Optimization & ATS Analysis Engine.

    Parameters
    ----------
    config : OptimizerConfig, optional
        Engine configuration. Defaults to DEFAULT_CONFIG if not provided.

    Attributes
    ----------
    ats_scorer : ATSScorer
        Computes 16-dimension ATS scores.
    keyword_optimizer : KeywordOptimizer
        Generates 9-category keyword analysis.
    section_analyzer : SectionAnalyzer
        Evaluates and suggests improvements for every resume section.
    gap_analyzer : GapAnalyzer
        Aggregates cross-job gaps into a career summary.

    Usage
    -----
        engine = ResumeOptimizationEngine()
        profile = engine.load_profile()
        reports = engine.analyze_all_jobs(profile, jobs[:20])
        summary = engine.generate_career_summary(profile, reports)
        engine.save_reports(reports, summary)
    """

    def __init__(self, config: OptimizerConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.ats_scorer = ATSScorer(self.config)
        self.keyword_optimizer = KeywordOptimizer(self.config)
        self.section_analyzer = SectionAnalyzer(self.config)
        self.gap_analyzer = GapAnalyzer(self.config)
        self.reports_dir = PROJECT_ROOT / self.config.reports_dir

    # =========================================================================
    # Profile loading
    # =========================================================================

    def load_profile(self) -> dict[str, Any]:
        """
        Load the CandidateProfile from the cache JSON file.

        Returns the profile as a plain dict for maximum compatibility with
        downstream analysis functions.

        Raises
        ------
        FileNotFoundError
            If the candidate profile cache does not exist.
        """
        profile_path = settings.cache_dir / "candidate_profile.json"
        if not profile_path.exists():
            raise FileNotFoundError(
                f"CandidateProfile cache not found at {profile_path}. "
                "Run the pipeline first to generate the profile."
            )
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        logger.info("CandidateProfile loaded from cache.")
        return data

    # =========================================================================
    # Per-job analysis
    # =========================================================================

    def analyze_job(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
    ) -> PerJobOptimizationReport:
        """
        Generate a complete optimization report for one resume vs one job.

        Parameters
        ----------
        profile : dict
            Serialised CandidateProfile.
        job : dict
            Serialised UniversalJobModel (model_dump()).

        Returns
        -------
        PerJobOptimizationReport
            Complete per-job optimization report.
        """
        # Extract job fields
        job_id = job.get("identity", {}).get("uuid", "unknown")
        job_title = job.get("job", {}).get("job_title", "Unknown Role")
        company_name = job.get("company", {}).get("company_name", "Unknown Company")
        job_description = job.get("job", {}).get("job_description", "")
        job_url = job.get("application", {}).get("application_url", "")
        required_skills = job.get("ai", {}).get("required_skills", [])
        tech_stack = job.get("ai", {}).get("technology_stack", [])
        job_keywords = job.get("ai", {}).get("job_keywords", [])
        job_location = job.get("location", {}).get("location", "")
        job_remote = job.get("location", {}).get("remote", False)
        job_min_exp = job.get("job", {}).get("minimum_experience")
        job_reliability = job.get("reliability", {}).get("reliability_score", 70.0)
        candidate_match_score = job.get("resume_match", {}).get("candidate_match_score")

        logger.debug(f"Analyzing: {job_title} @ {company_name}")

        # ── 1. ATS Score ──────────────────────────────────────────────────────
        ats_scorecard = self.ats_scorer.score(
            profile=profile,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            job_required_skills=required_skills,
            job_tech_stack=tech_stack,
            job_keywords=job_keywords,
            job_location=job_location,
            job_remote=job_remote,
            job_min_exp=job_min_exp,
            job_reliability=job_reliability,
            candidate_match_score=candidate_match_score,
        )

        # ── 2. Keyword Analysis ───────────────────────────────────────────────
        keyword_analysis = self.keyword_optimizer.analyze(
            profile=profile,
            job_id=job_id,
            job_description=job_description,
            job_keywords=job_keywords,
            job_tech_stack=tech_stack,
        )

        # ── 3. Section Analysis ───────────────────────────────────────────────
        sections_analysis = self.section_analyzer.analyze(
            profile=profile,
            job_id=job_id,
            job_description=job_description,
            job_tech_stack=tech_stack,
            job_required_skills=required_skills,
        )

        # ── 4. Per-item analyses ──────────────────────────────────────────────
        project_analyses = self.section_analyzer.analyze_projects(
            profile=profile,
            job_description=job_description,
            job_tech_stack=tech_stack,
        )
        internship_analyses = self.section_analyzer.analyze_internships(
            profile=profile,
            job_description=job_description,
            job_tech_stack=tech_stack,
        )
        certification_analyses = self.section_analyzer.analyze_certifications(
            profile=profile,
            job_description=job_description,
        )

        # ── 5. Suggestions ────────────────────────────────────────────────────
        suggestions = self._generate_suggestions(
            profile=profile,
            job_title=job_title,
            company_name=company_name,
            ats_scorecard=ats_scorecard,
            keyword_analysis=keyword_analysis,
            sections_analysis=sections_analysis,
            project_analyses=project_analyses,
            internship_analyses=internship_analyses,
        )

        # ── 6. Version Recommendation ─────────────────────────────────────────
        version_rec = self._version_recommendation(job_id, job_title, profile)

        # ── 7. Improvement Score Card ─────────────────────────────────────────
        improvement = self._improvement_scorecard(
            ats_scorecard.overall_ats_score,
            candidate_match_score or 0,
            suggestions,
        )

        return PerJobOptimizationReport(
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            job_url=job_url,
            candidate_name=profile.get("personal", {}).get("name", ""),
            generated_at=datetime.now().isoformat(),
            ats_scorecard=ats_scorecard,
            keyword_analysis=keyword_analysis,
            sections_analysis=sections_analysis,
            project_analyses=project_analyses,
            internship_analyses=internship_analyses,
            certification_analyses=certification_analyses,
            suggestions=suggestions,
            version_recommendation=version_rec,
            improvement_scorecard=improvement,
        )

    def analyze_all_jobs(
        self,
        profile: dict[str, Any],
        jobs: list[dict[str, Any]],
    ) -> list[PerJobOptimizationReport]:
        """
        Analyze multiple jobs and return one report per job.

        Processes up to config.top_n_jobs jobs. If a job fails, a warning is
        logged and the job is skipped — the rest continue.

        Parameters
        ----------
        profile : dict
            Serialised CandidateProfile.
        jobs : list[dict]
            List of serialised UniversalJobModel objects, sorted by match score
            (highest first). Only the top top_n_jobs are analyzed.

        Returns
        -------
        list[PerJobOptimizationReport]
        """
        top_jobs = jobs[: self.config.top_n_jobs]
        logger.info(f"Analyzing {len(top_jobs)} jobs (top {self.config.top_n_jobs} from {len(jobs)} total).")

        reports = []
        t0 = time.time()

        for i, job in enumerate(top_jobs, start=1):
            job_title = job.get("job", {}).get("job_title", "Unknown")
            try:
                report = self.analyze_job(profile, job)
                reports.append(report)
                if i % 5 == 0:
                    logger.info(f"  Analyzed {i}/{len(top_jobs)} jobs…")
            except Exception as exc:
                logger.warning(f"  Job {i} ('{job_title}') failed: {exc} — skipping.")

        elapsed = time.time() - t0
        logger.info(
            f"Resume optimization complete: {len(reports)}/{len(top_jobs)} reports "
            f"generated in {elapsed:.1f}s."
        )
        return reports

    # =========================================================================
    # Career summary
    # =========================================================================

    def generate_career_summary(
        self,
        profile: dict[str, Any],
        reports: list[PerJobOptimizationReport],
    ) -> CareerSummaryReport:
        """
        Aggregate per-job reports into an overall career summary.

        Parameters
        ----------
        profile : dict
            Serialised CandidateProfile.
        reports : list[PerJobOptimizationReport]
            All per-job reports from analyze_all_jobs().

        Returns
        -------
        CareerSummaryReport
        """
        logger.info("Generating career summary report…")
        return self.gap_analyzer.generate_career_summary(profile, reports)

    # =========================================================================
    # Persistence
    # =========================================================================

    def save_reports(
        self,
        reports: list[PerJobOptimizationReport],
        summary: CareerSummaryReport | None = None,
    ) -> Path:
        """
        Save all reports to cache/resume_reports/.

        Files written:
        - cache/resume_reports/<uuid>_report.json  (one per job)
        - cache/resume_reports/career_summary.json  (aggregated)
        - cache/resume_reports/latest_reports.json  (index of latest batch)

        Parameters
        ----------
        reports : list[PerJobOptimizationReport]
        summary : CareerSummaryReport, optional

        Returns
        -------
        Path : The reports directory.
        """
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Per-job reports
        for report in reports:
            fname = self.reports_dir / f"{report.job_id[:16]}_report.json"
            fname.write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8",
            )

        # Career summary
        if summary:
            summary_path = self.reports_dir / "career_summary.json"
            summary_path.write_text(
                summary.model_dump_json(indent=2),
                encoding="utf-8",
            )
            logger.info(f"Career summary saved to {summary_path}")

        # Latest reports index
        index = {
            "generated_at": datetime.now().isoformat(),
            "total_reports": len(reports),
            "reports": [
                {
                    "job_id": r.job_id,
                    "job_title": r.job_title,
                    "company_name": r.company_name,
                    "ats_score": r.ats_scorecard.overall_ats_score,
                    "fit_category": r.ats_scorecard.fit_category,
                    "file": f"{r.job_id[:16]}_report.json",
                }
                for r in sorted(
                    reports,
                    key=lambda r: r.ats_scorecard.overall_ats_score,
                    reverse=True,
                )
            ],
        }
        index_path = self.reports_dir / "latest_reports.json"
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        logger.info(f"Saved {len(reports)} optimization reports to {self.reports_dir}")
        return self.reports_dir

    def top_email_suggestions(
        self, reports: list[PerJobOptimizationReport]
    ) -> list[str]:
        """
        Return the top N suggestion texts formatted for inclusion in the daily email.

        Aggregates suggestions across all reports, deduplicates, and returns the
        top config.max_suggestions_in_email by priority.
        """
        from collections import Counter
        seen: dict[str, ResumeSuggestion] = {}
        counts: Counter = Counter()

        for report in reports:
            for sug in report.suggestions:
                key = sug.action[:80].lower()
                counts[key] += 1
                if key not in seen:
                    seen[key] = sug

        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        top = sorted(
            seen.values(),
            key=lambda s: (priority_order.get(s.priority, 2), -counts[s.action[:80].lower()]),
        )[: self.config.max_suggestions_in_email]

        return [
            f"[{s.priority}] {s.action} — {s.why[:120]}"
            for s in top
        ]

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _generate_suggestions(
        self,
        profile: dict[str, Any],
        job_title: str,
        company_name: str,
        ats_scorecard: Any,
        keyword_analysis: Any,
        sections_analysis: Any,
        project_analyses: list,
        internship_analyses: list,
    ) -> list[ResumeSuggestion]:
        """
        Compile all improvement suggestions from analysis results.

        Sources:
        1. Missing keywords → suggest incorporating them naturally.
        2. Low-scoring sections → forward their section suggestions.
        3. Project reordering → from project analysis.
        4. ATS score gaps → dimension-specific suggestions.

        All suggestions include: action, why, jobs_benefited, impact, priority.
        """
        suggestions: list[ResumeSuggestion] = []
        job_ref = f"{job_title} @ {company_name}"

        # ── From keyword analysis ─────────────────────────────────────────────
        if keyword_analysis.missing_keywords:
            top_missing = keyword_analysis.missing_keywords[:5]
            suggestions.append(ResumeSuggestion(
                suggestion_id="kw_missing",
                action=f"Incorporate missing keywords: {', '.join(top_missing[:3])}",
                section="Skills / Projects / Summary",
                why=(
                    f"These keywords appear in the JD but are absent from your resume. "
                    f"ATS systems score keyword density — adding them naturally can lift your score."
                ),
                jobs_benefited=[job_ref],
                estimated_impact="+5–10 ATS points",
                priority="High" if len(top_missing) >= 3 else "Medium",
            ))

        if keyword_analysis.recommended_keywords:
            top_rec = keyword_analysis.recommended_keywords[:3]
            suggestions.append(ResumeSuggestion(
                suggestion_id="kw_recommended",
                action=f"Add recommended keywords: {', '.join(top_rec)}",
                section="Skills",
                why=(
                    f"These high-signal terms are in the JD's explicit keyword list and tech stack "
                    f"but are missing from your resume."
                ),
                jobs_benefited=[job_ref],
                estimated_impact="+3–7 ATS points",
                priority="High",
            ))

        # ── From section analysis ─────────────────────────────────────────────
        sections = [
            ("Header", sections_analysis.header),
            ("Summary", sections_analysis.summary),
            ("Projects", sections_analysis.projects),
            ("Internships", sections_analysis.internships),
            ("Skills", sections_analysis.skills),
            ("Certifications", sections_analysis.certifications),
        ]
        for sec_name, sec_report in sections:
            if sec_report.score < 60 and sec_report.suggestions:
                top_sug = sec_report.suggestions[0]
                priority = "High" if sec_report.score < 40 else "Medium"
                suggestions.append(ResumeSuggestion(
                    suggestion_id=f"section_{sec_name.lower()}",
                    action=top_sug,
                    section=sec_name,
                    why=f"{sec_name} section score is {sec_report.score:.0f}/100 — below optimal threshold.",
                    jobs_benefited=[job_ref],
                    estimated_impact=f"+{int((80 - sec_report.score) * 0.1)} section score points",
                    priority=priority,
                ))

        # ── From project analysis ─────────────────────────────────────────────
        for proj_a in project_analyses[:3]:
            if proj_a.recommendation in ("Move Up", "Highlight", "Expand"):
                suggestions.append(ResumeSuggestion(
                    suggestion_id=f"proj_{proj_a.project_name[:20].lower().replace(' ', '_')}",
                    action=f"{proj_a.recommendation}: '{proj_a.project_name[:40]}'",
                    section="Projects",
                    why=proj_a.reason,
                    jobs_benefited=[job_ref],
                    estimated_impact="+2–5 ATS points",
                    priority="Medium" if proj_a.recommendation == "Expand" else "High",
                ))

        # ── From ATS dimension gaps ───────────────────────────────────────────
        sc = ats_scorecard
        if sc.skills_score.score < 50 and sc.skills_score.missing_items:
            suggestions.append(ResumeSuggestion(
                suggestion_id="ats_skills_gap",
                action=(
                    f"Add missing skills to your skills section: "
                    f"{', '.join(sc.skills_score.missing_items[:3])}"
                ),
                section="Skills",
                why=f"Skills score is {sc.skills_score.score:.0f}/100 — {len(sc.skills_score.missing_items)} required skills are absent.",
                jobs_benefited=[job_ref],
                estimated_impact="+8–12 ATS points",
                priority="High",
            ))

        if sc.recruiter_appeal_score.score < 50:
            suggestions.append(ResumeSuggestion(
                suggestion_id="recruiter_appeal",
                action="Add GitHub, LinkedIn, and portfolio links to your resume header",
                section="Header",
                why=(
                    f"Recruiter appeal score is {sc.recruiter_appeal_score.score:.0f}/100. "
                    "Missing profile links reduce recruiter confidence significantly."
                ),
                jobs_benefited=[job_ref],
                estimated_impact="+5–8 ATS points",
                priority="High",
            ))

        # Deduplicate and sort by priority
        seen_actions: set[str] = set()
        unique_suggestions = []
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        for sug in sorted(suggestions, key=lambda s: priority_order.get(s.priority, 2)):
            key = sug.action[:60].lower()
            if key not in seen_actions:
                seen_actions.add(key)
                unique_suggestions.append(sug)

        return unique_suggestions[:10]

    def _version_recommendation(
        self,
        job_id: str,
        job_title: str,
        profile: dict[str, Any],
    ) -> ResumeVersionRecommendation:
        """
        Recommend the best resume version for this job.

        Currently detects available resume files from the resume/ directory.
        Designed for future multi-version support.
        """
        resume_dir = settings.resume_dir if hasattr(settings, "resume_dir") else PROJECT_ROOT / "resume"
        available = []
        if resume_dir.exists():
            available = [f.name for f in resume_dir.iterdir()
                         if f.suffix.lower() in (".pdf", ".docx", ".doc")]

        title_lower = job_title.lower()
        if "ai" in title_lower or "ml" in title_lower or "llm" in title_lower:
            best = "AI Resume"
        elif "backend" in title_lower or "api" in title_lower or "django" in title_lower:
            best = "Backend Resume"
        elif "data" in title_lower or "analyst" in title_lower:
            best = "Data Resume"
        elif "frontend" in title_lower or "react" in title_lower:
            best = "Frontend Resume"
        else:
            best = "General Resume"

        if len(available) <= 1:
            reason = (
                f"Only one resume detected in resume/ directory ({available[0] if available else 'none'}). "
                f"The {best} version is recommended for this role type — consider creating a tailored version."
            )
        else:
            reason = f"Based on job title '{job_title}', the {best} is the best match."

        tips = []
        if best == "AI Resume":
            tips = [
                "Ensure LangChain, RAG, and LLM are prominent in the skills and projects sections.",
                "Move AI/ML projects above backend projects.",
                "Add any Generative AI experience to the summary.",
            ]
        elif best == "Backend Resume":
            tips = [
                "Lead with FastAPI/Django/Flask experience.",
                "Emphasize database and API design projects.",
                "Add performance metrics if available (e.g., 'Reduced API latency by X%').",
            ]

        return ResumeVersionRecommendation(
            job_id=job_id,
            best_version=best,
            available_versions=available,
            reason=reason,
            customization_tips=tips,
        )

    def _improvement_scorecard(
        self,
        current_ats: float,
        current_match: float,
        suggestions: list[ResumeSuggestion],
    ) -> ImprovementScoreCard:
        """
        Estimate the score improvement from implementing all suggestions.

        Methodology:
        - Each High priority suggestion adds 5–10 ATS points.
        - Each Medium priority suggestion adds 2–5 ATS points.
        - Low priority adds 1–2 points.
        - Optimized score is capped at 95 (a perfect resume doesn't exist).
        - Confidence is Medium unless we have very few suggestions (Low)
          or the current score is already high (also Low).
        """
        high = [s for s in suggestions if s.priority == "High"]
        medium = [s for s in suggestions if s.priority == "Medium"]
        low = [s for s in suggestions if s.priority == "Low"]

        ats_gain = min(len(high) * 7.0 + len(medium) * 3.0 + len(low) * 1.5, 25.0)
        match_gain = ats_gain * 0.6  # Match improvement is roughly 60% of ATS improvement

        optimized_ats = min(current_ats + ats_gain, 95.0)
        optimized_match = min(current_match + match_gain, 95.0)

        confidence = (
            "Low" if current_ats >= 80 or len(suggestions) < 2 else
            "High" if len(high) >= 3 else
            "Medium"
        )

        return ImprovementScoreCard(
            current_ats_score=current_ats,
            optimized_ats_score=round(optimized_ats, 2),
            expected_ats_improvement=round(ats_gain, 2),
            current_match_score=float(current_match),
            optimized_match_score=round(optimized_match, 2),
            expected_match_improvement=round(match_gain, 2),
            confidence=confidence,
            methodology=(
                f"Estimated improvement: {len(high)} High-priority suggestions (×7 pts each), "
                f"{len(medium)} Medium (×3 pts), {len(low)} Low (×1.5 pts). "
                f"Total: +{ats_gain:.1f} ATS points. Capped at 95. "
                "Actual improvement depends on how changes are implemented."
            ),
        )
