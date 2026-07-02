"""
resume_optimizer/gap_analyzer.py — Cross-Job Skill & Career Gap Analyzer
=========================================================================
Purpose
-------
Aggregate skill, technology, and certification gaps across ALL matched jobs
to generate a prioritized learning path and career growth recommendations.

Design Philosophy
-----------------
- Items are only flagged as gaps if they appear in a statistically meaningful
  fraction of analyzed jobs (configurable frequency thresholds).
- Never fabricates gaps: every item in the report references actual JD data.
- The learning path is ordered by impact-to-effort ratio.
- Career recommendations are evidence-based (frequency statistics).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from resume_optimizer.config import OptimizerConfig
from resume_optimizer.models import (
    CareerRecommendation,
    CareerSummaryReport,
    GapAnalysisReport,
    GapItem,
    LearningPathItem,
    PerJobOptimizationReport,
    ResumeSuggestion,
)


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


class GapAnalyzer:
    """
    Generates a cross-job gap analysis and career summary from a list of
    per-job optimization reports.

    Parameters
    ----------
    config : OptimizerConfig
        Engine configuration with gap analysis thresholds.

    Usage
    -----
        analyzer = GapAnalyzer(config)
        summary = analyzer.generate_career_summary(profile, reports)
    """

    def __init__(self, config: OptimizerConfig) -> None:
        self.config = config
        self.gap_cfg = config.gap_config

    def generate_career_summary(
        self,
        profile: dict[str, Any],
        reports: list[PerJobOptimizationReport],
    ) -> CareerSummaryReport:
        """
        Aggregate all per-job reports into a career summary.

        Algorithm:
        1. Count frequency of every missing keyword/skill across all reports.
        2. Keep only items above the configured frequency threshold.
        3. Assign priority based on frequency band.
        4. Build an ordered learning path from the top gaps.
        5. Generate career recommendations sorted by frequency.

        Parameters
        ----------
        profile : dict
            Serialised CandidateProfile.
        reports : list[PerJobOptimizationReport]
            All per-job optimization reports for this run.

        Returns
        -------
        CareerSummaryReport
        """
        if not reports:
            return CareerSummaryReport(
                candidate_name=profile.get("personal", {}).get("name", ""),
                generated_at=datetime.now().isoformat(),
                total_jobs_analyzed=0,
            )

        n = len(reports)
        candidate_name = profile.get("personal", {}).get("name", "")

        # ── Aggregate missing keywords across all reports ─────────────────────
        missing_kw_counts: Counter = Counter()
        missing_tech_counts: Counter = Counter()
        missing_cert_counts: Counter = Counter()
        all_jd_keywords: Counter = Counter()
        all_jd_techs: Counter = Counter()
        all_jd_frameworks: Counter = Counter()

        for report in reports:
            kw = report.keyword_analysis
            for kw_token in kw.missing_keywords:
                missing_kw_counts[_normalize(kw_token)] += 1
            for kw_token in kw.matched_keywords + kw.recommended_keywords:
                all_jd_keywords[_normalize(kw_token)] += 1

            sc = report.ats_scorecard
            for tech in sc.technology_match_score.missing_items:
                missing_tech_counts[_normalize(tech)] += 1
            for tech in sc.technology_match_score.matched_items:
                all_jd_techs[_normalize(tech)] += 1

            for cert_a in report.certification_analyses:
                if cert_a.relevance_score < 60:
                    missing_cert_counts[_normalize(cert_a.certification_name)] += 0  # not missing; already has it
            # Look at recommended keywords for cert signals
            for kw_token in kw.recommended_keywords:
                if any(c in kw_token for c in ["certified", "certification", "aws", "google cloud", "azure", "coursera"]):
                    missing_cert_counts[_normalize(kw_token)] += 1

            # Frameworks
            for kw_token in kw.industry_standard_keywords:
                all_jd_frameworks[_normalize(kw_token)] += 1

        # ── Build gap items ───────────────────────────────────────────────────
        gap_skills = self._build_gap_items(
            missing_kw_counts, n, self.gap_cfg.missing_skill_frequency_threshold, "skill"
        )
        gap_techs = self._build_gap_items(
            missing_tech_counts, n, self.gap_cfg.missing_tech_frequency_threshold, "technology"
        )
        gap_certs = self._build_gap_items(
            missing_cert_counts, n, self.gap_cfg.missing_cert_frequency_threshold, "certification"
        )

        # ── Recommended projects to build ─────────────────────────────────────
        recommended_projects = self._infer_recommended_projects(
            gap_techs, all_jd_keywords
        )

        # ── Learning path ─────────────────────────────────────────────────────
        learning_path = self._build_learning_path(gap_skills + gap_techs + gap_certs)

        # ── Career recommendations ────────────────────────────────────────────
        career_recs = self._build_career_recommendations(
            reports, all_jd_keywords, all_jd_techs, all_jd_frameworks, n
        )

        # ── Most valuable skills / techs / certs / frameworks ─────────────────
        freq_threshold = max(1, int(n * 0.20))
        most_valuable_skills = [k for k, v in all_jd_keywords.most_common(15) if v >= freq_threshold]
        most_requested_technologies = [k for k, v in all_jd_techs.most_common(10) if v >= freq_threshold]
        most_requested_certifications = [
            k for k, v in missing_cert_counts.most_common(5) if v >= 1
        ]
        most_requested_frameworks = [k for k, v in all_jd_frameworks.most_common(10) if v >= freq_threshold]

        # ── Best fit jobs ─────────────────────────────────────────────────────
        sorted_reports = sorted(
            reports, key=lambda r: r.ats_scorecard.overall_ats_score, reverse=True
        )
        best_fit_jobs = [
            f"{r.job_title} @ {r.company_name} ({r.ats_scorecard.overall_ats_score:.0f}/100)"
            for r in sorted_reports[:5]
        ]

        # ── Average ATS score ─────────────────────────────────────────────────
        avg_ats = sum(r.ats_scorecard.overall_ats_score for r in reports) / n

        # ── Top universal suggestions ─────────────────────────────────────────
        suggestion_counts: Counter = Counter()
        all_suggestions: dict[str, ResumeSuggestion] = {}
        for report in reports:
            for sug in report.suggestions:
                key = _normalize(sug.action)[:60]
                suggestion_counts[key] += 1
                all_suggestions[key] = sug
        top_universal = [
            all_suggestions[k]
            for k, _ in suggestion_counts.most_common(3)
            if k in all_suggestions
        ]

        # ── Career growth suggestions ─────────────────────────────────────────
        growth_suggestions = self._career_growth_suggestions(
            profile, gap_skills, gap_techs, most_requested_technologies
        )

        return CareerSummaryReport(
            candidate_name=candidate_name,
            generated_at=datetime.now().isoformat(),
            total_jobs_analyzed=n,
            average_ats_score=round(avg_ats, 2),
            best_fit_jobs=best_fit_jobs,
            gap_analysis=GapAnalysisReport(
                top_missing_skills=gap_skills[:10],
                top_missing_technologies=gap_techs[:10],
                top_missing_certifications=gap_certs[:5],
                recommended_projects=recommended_projects,
                learning_path=learning_path,
                total_estimated_weeks=sum(i.estimated_weeks for i in learning_path),
            ),
            career_recommendations=career_recs[:10],
            most_valuable_skills=most_valuable_skills,
            most_requested_technologies=most_requested_technologies,
            most_requested_certifications=most_requested_certifications,
            most_requested_frameworks=most_requested_frameworks,
            best_projects_to_build=recommended_projects,
            career_growth_suggestions=growth_suggestions,
            top_universal_suggestions=top_universal,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_gap_items(
        self,
        counts: Counter,
        total_jobs: int,
        threshold: float,
        category: str,
    ) -> list[GapItem]:
        """
        Convert a frequency counter into GapItem objects.

        Only items above the frequency threshold are included.
        Priority is assigned based on frequency bands.
        """
        items = []
        for name, count in counts.most_common(20):
            freq = count / total_jobs
            if freq < threshold or not name.strip():
                continue

            priority = (
                "High" if freq >= self.gap_cfg.high_priority_threshold else
                "Medium" if freq >= self.gap_cfg.medium_priority_threshold else
                "Low"
            )

            # Estimate weeks from config table
            weeks = self.gap_cfg.learning_time_estimates.get(
                name, self.gap_cfg.learning_time_estimates["default"]
            )

            items.append(GapItem(
                name=name,
                frequency_pct=round(freq * 100, 1),
                priority=priority,
                estimated_weeks=weeks,
                reason=(
                    f"Required or preferred in {count} of {total_jobs} analyzed jobs "
                    f"({freq*100:.0f}%) — {priority} priority gap."
                ),
            ))
        return items

    def _infer_recommended_projects(
        self, gap_techs: list[GapItem], all_jd_keywords: Counter
    ) -> list[str]:
        """
        Suggest project types based on the most common missing technologies.
        """
        recommendations = []
        top_gap_techs = {g.name for g in gap_techs[:5]}

        # Project templates based on common tech gaps
        project_templates = [
            ({"docker", "kubernetes", "ci/cd"}, "Containerized microservice with Docker + CI/CD pipeline"),
            ({"aws", "gcp", "azure", "cloud"}, "Cloud-deployed web application with serverless functions"),
            ({"rag", "langchain", "embeddings", "vector"}, "RAG-based Q&A chatbot using LangChain and a vector database"),
            ({"typescript", "react", "next.js"}, "Full-stack application with Next.js + TypeScript + REST API"),
            ({"spark", "airflow", "etl", "pipeline"}, "Data pipeline with Airflow orchestration and Spark processing"),
            ({"pytorch", "tensorflow", "deep learning"}, "Deep learning model training and serving project"),
            ({"kafka", "redis", "microservices"}, "Event-driven microservices application with Kafka messaging"),
        ]

        for tech_set, template in project_templates:
            if tech_set & top_gap_techs:
                recommendations.append(template)

        if not recommendations:
            recommendations.append("RAG-based AI assistant with a FastAPI backend and PostgreSQL storage")
            recommendations.append("REST API with authentication, database, and unit tests")

        return recommendations[:5]

    def _build_learning_path(self, all_gaps: list[GapItem]) -> list[LearningPathItem]:
        """
        Build an ordered learning path from the combined gap items.

        Ordering strategy: High priority first, then sorted by
        estimated weeks ascending (shortest wins first = quick wins first).
        """
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_gaps = sorted(
            all_gaps,
            key=lambda g: (priority_order.get(g.priority, 2), g.estimated_weeks)
        )

        path = []
        for i, gap in enumerate(sorted_gaps[:8], start=1):
            path.append(LearningPathItem(
                order=i,
                action=f"Learn {gap.name}",
                rationale=gap.reason,
                estimated_weeks=gap.estimated_weeks,
                priority=gap.priority,
            ))

        return path

    def _build_career_recommendations(
        self,
        reports: list[PerJobOptimizationReport],
        all_kw: Counter,
        all_techs: Counter,
        all_frameworks: Counter,
        total_jobs: int,
    ) -> list[CareerRecommendation]:
        """
        Generate evidence-based career recommendations from job frequency data.
        """
        recs = []

        # Top skills
        for skill, count in all_kw.most_common(5):
            freq = count / total_jobs
            if freq < 0.15 or len(skill) < 3:
                continue
            benefiting_jobs = [
                f"{r.job_title} @ {r.company_name}"
                for r in reports
                if skill in r.keyword_analysis.recommended_keywords or
                   skill in r.keyword_analysis.missing_keywords
            ][:3]
            recs.append(CareerRecommendation(
                category="Skill",
                item=f"Strengthen {skill}",
                frequency_pct=round(freq * 100, 1),
                why=f"'{skill}' appears in {count} of {total_jobs} analyzed jobs.",
                priority="High" if freq >= 0.40 else "Medium",
                jobs_benefited=benefiting_jobs,
                estimated_impact_points=min(int(freq * 15), 10),
            ))

        # Top technologies
        for tech, count in all_techs.most_common(5):
            freq = count / total_jobs
            if freq < 0.15 or len(tech) < 3:
                continue
            recs.append(CareerRecommendation(
                category="Technology",
                item=f"Learn {tech}",
                frequency_pct=round(freq * 100, 1),
                why=f"'{tech}' is in the tech stack of {count} of {total_jobs} analyzed jobs.",
                priority="High" if freq >= 0.35 else "Medium",
                jobs_benefited=[],
                estimated_impact_points=min(int(freq * 20), 15),
            ))

        return sorted(recs, key=lambda r: r.frequency_pct, reverse=True)

    def _career_growth_suggestions(
        self,
        profile: dict[str, Any],
        gap_skills: list[GapItem],
        gap_techs: list[GapItem],
        top_techs: list[str],
    ) -> list[str]:
        """
        Generate high-level career trajectory suggestions based on gaps.
        """
        suggestions = []
        level = profile.get("experience", {}).get("level", "Fresher")
        skills_flat = []
        for v in profile.get("skills", {}).values():
            if isinstance(v, list):
                skills_flat.extend(s.lower() for s in v)

        if level in ("Fresher", "Junior"):
            suggestions.append(
                "Focus on building 2–3 end-to-end projects that you can deploy and demo — "
                "they matter more than certifications at the fresher stage."
            )
            suggestions.append(
                "Contribute to open source projects to build your GitHub presence."
            )

        if gap_techs:
            top_gap = gap_techs[0].name
            suggestions.append(
                f"Prioritize learning '{top_gap}' — it appears in the most job descriptions "
                "and would improve your match scores the most."
            )

        if "docker" in top_techs and "docker" not in skills_flat:
            suggestions.append(
                "Learn Docker (containerization) — it's requested by nearly every modern tech company "
                "and takes only 2–3 weeks to become productive."
            )

        if not profile.get("experience", {}).get("internships"):
            suggestions.append(
                "Apply aggressively to internships — even a 1–2 month virtual internship significantly "
                "improves ATS scores and recruiter confidence."
            )

        suggestions.append(
            "Keep your GitHub active — push code, document your projects well, "
            "and add README files with architecture diagrams."
        )

        return suggestions[:5]
