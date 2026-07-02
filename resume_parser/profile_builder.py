"""
resume_parser/profile_builder.py — Candidate Profile Builder Orchestrator
========================================================================
Purpose
-------
Coordinate all parser subsystems (Detector, Extractor, SectionParser,
SkillExpander, InferenceEngine, KeywordGenerator, QueryGenerator, Scorer,
ChangeDetector, CacheManager) to construct a complete CandidateProfile.

Design Decisions
----------------
Orchestrated pipeline:
    - This is the main implementation layer of Phase 3.
    - It handles:
      1. Finding the newest resume.
      2. Checking cache. If cache hit → return profile.
      3. If cache miss → extract text, parse sections, expand skills,
         infer roles, generate keyword groups and search queries, compute scores.
      4. Compare with the previously cached profile (if any) to populate the
         `change_report` field.
      5. Cache the final profile.

Usage
-----
    from resume_parser.profile_builder import ProfileBuilder

    builder = ProfileBuilder()
    profile = builder.build()
    print(profile.personal.name)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from resume_parser.profile_model import CandidateProfile, ProfileMeta
from resume_parser.detector import ResumeDetector
from resume_parser.extractor import ResumeExtractor
from resume_parser.section_parser import SectionParser
from resume_parser.skill_expander import SkillExpander
from resume_parser.inference_engine import InferenceEngine
from resume_parser.keyword_generator import KeywordGenerator
from resume_parser.query_generator import QueryGenerator
from resume_parser.scorer import CandidateScorer
from resume_parser.change_detector import ResumeChangeDetector
from resume_parser.cache_manager import CacheManager
from utils.logger import get_logger

logger = get_logger(__name__)


class ProfileBuilder:
    """
    Orchestrates the resume parsing and intelligence pipeline.
    """

    def __init__(
        self,
        resume_dir: Path | None = None,
        cache_dir: Path | None = None,
        preferred_locations: list[str] | None = None
    ) -> None:
        self.resume_dir = resume_dir or settings.resume_dir
        self.cache_dir = cache_dir or settings.cache_dir
        self.preferred_locations = preferred_locations or settings.preferred_locations

        self.detector = ResumeDetector(resume_dir=self.resume_dir)
        self.extractor = ResumeExtractor()
        self.section_parser = SectionParser()
        self.skill_expander = SkillExpander()
        self.inference_engine = InferenceEngine()
        self.keyword_generator = KeywordGenerator()
        self.query_generator = QueryGenerator()
        self.scorer = CandidateScorer()
        self.change_detector = ResumeChangeDetector()
        self.cache = CacheManager(cache_dir=self.cache_dir)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def build(self, *, force_rebuild: bool = False) -> CandidateProfile:
        """
        Build the CandidateProfile for the newest resume.

        Uses the cached profile if the resume is unchanged, unless
        `force_rebuild` is set to True.

        Parameters
        ----------
        force_rebuild : bool
            If True, invalidates cache and rebuilds from raw file.

        Returns
        -------
        CandidateProfile
            The fully populated and cached profile.
        """
        # 1. Locate the newest resume
        resume_path = self.detector.find_newest()

        # 2. Check Cache
        if not force_rebuild:
            cached = self.cache.load_profile(resume_path)
            if cached:
                return cached

        logger.info("Building profile from scratch", extra={"resume": str(resume_path)})

        # Load old profile if exists to perform diffing
        old_profile = self._load_old_profile_raw()

        # 3. Extract text
        raw_text = self.extractor.extract(resume_path)

        # 4. Parse sections and entities
        parsed = self.section_parser.parse(raw_text)

        # 5. Extract flat list of skills
        skills_section = parsed["skills"]
        flat_skills = self._get_flat_skills_list(skills_section)

        # 6. Skill Expansion
        expanded_mapping = self.skill_expander.expand(flat_skills)
        flat_expansions = self.skill_expander.get_flat_expansions(flat_skills)

        # 7. Role Inference
        inferred_roles = self.inference_engine.infer(flat_expansions)

        # 8. Score Calculation & Strengths
        personal = parsed["personal"]
        education = parsed["education"]
        experience = parsed["experience"]
        projects = parsed["projects"]
        hackathons = parsed["hackathons"]
        certifications = parsed["certifications"]
        raw_sections = parsed["raw_sections"]

        # If locations are override in config, use them, else infer from resume contact details
        active_locations = self.preferred_locations
        if not active_locations and personal.get("location"):
            active_locations = [personal["location"]]

        scoring_results = self.scorer.score_profile(
            sections=raw_sections,
            personal=personal,
            education=education,
            skills=skills_section,
            experience=experience,
            projects=projects,
            hackathons=hackathons,
            certifications=certifications
        )

        # 9. Keyword Generation
        keyword_groups = self.keyword_generator.generate(
            skills=flat_skills,
            expanded_keywords=flat_expansions,
            inferred_roles=inferred_roles,
            preferred_locations=active_locations
        )

        # 10. Query Generation
        search_queries = self.query_generator.generate_queries(
            roles=inferred_roles,
            locations=active_locations,
            experience_level=experience["level"],
            graduation_year=education.get("graduation_year")
        )

        # 11. Profile Construction
        all_resumes = self.detector.list_all()
        archived = [r.name for r in all_resumes if r.resolve() != resume_path.resolve()]

        meta = ProfileMeta(
            resume_path=str(resume_path.resolve()),
            resume_hash=self.cache.get_current_hash(resume_path),
            resume_filename=resume_path.name,
            archived_resumes=archived
        )

        # Categorise flat skills list
        tech_groups = {
            "backend": [], "ai": [], "ml": [], "cloud": []
        }
        backend_kws = {"python", "fastapi", "django", "flask", "postgresql", "mysql", "sqlite", "redis", "node", "express", "go", "golang", "java", "sql", "api", "rest"}
        ai_kws = {"langchain", "llamaindex", "openai", "gemini", "claude", "rag", "agent", "generative ai", "prompt", "llm", "transformers", "huggingface"}
        ml_kws = {"pytorch", "tensorflow", "scikit-learn", "keras", "machine learning", "deep learning", "nlp", "computer vision", "pandas", "numpy", "matplotlib", "seaborn"}
        cloud_kws = {"aws", "azure", "gcp", "docker", "kubernetes", "git", "ci/cd", "github actions"}

        for s in flat_skills:
            s_low = s.lower()
            if any(kw in s_low for kw in backend_kws):
                tech_groups["backend"].append(s)
            if any(kw in s_low for kw in ai_kws):
                tech_groups["ai"].append(s)
            if any(kw in s_low for kw in ml_kws):
                tech_groups["ml"].append(s)
            if any(kw in s_low for kw in cloud_kws):
                tech_groups["cloud"].append(s)

        # Languages spoken
        spoken_langs = skills_section.get("languages_spoken", []) or parsed.get("languages", []) or []

        profile = CandidateProfile(
            meta=meta,
            personal=personal,
            education=education,
            experience=experience,
            skills=skills_section,
            projects=projects,
            certifications=certifications,
            hackathons=hackathons,
            awards=parsed["awards"],
            publications=parsed["publications"],
            open_source=parsed["open_source"],
            volunteer=parsed["volunteer"],
            expanded_keywords=expanded_mapping,
            inferred_roles=inferred_roles,
            keyword_groups=keyword_groups,
            search_queries=search_queries,
            candidate_analysis={
                "strengths": scoring_results["strengths"],
                "experience_level": experience["level"],
                "career_readiness_score": scoring_results["career_readiness_score"],
                "ats_score": scoring_results["ats_score"],
                "preferred_roles": [r.title for r in inferred_roles[:3]],
                "preferred_industries": scoring_results["career_domains"],
                "preferred_locations": active_locations,
                "career_domains": scoring_results["career_domains"],
                "preferred_companies": ["Google", "Nvidia", "Microsoft", "OpenAI", "Anthropic"],
                "preferred_domains": scoring_results["career_domains"],
                "backend_technologies": tech_groups["backend"],
                "ai_technologies": tech_groups["ai"],
                "ml_technologies": tech_groups["ml"],
                "cloud_skills": tech_groups["cloud"],
                "languages": spoken_langs
            },
            resume_summary=parsed["resume_summary"]
        )

        # 12. Change Detection (Diff)
        if old_profile:
            diff_report = self.change_detector.detect_changes(old_profile, profile)
            profile.change_report = diff_report

        # 13. Save to Cache
        self.cache.save_profile(profile, resume_path)

        logger.info(
            "Candidate profile successfully built and cached",
            extra={
                "candidate_name": profile.personal.name,
                "skills_count": len(flat_skills),
                "queries_count": len(search_queries)
            }
        )

        return profile

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _get_flat_skills_list(self, skills_section: dict[str, list[str]]) -> list[str]:
        """Convert categorised skills dict to a unique flat list."""
        flat = set()
        for key, val in skills_section.items():
            if isinstance(val, list):
                for s in val:
                    flat.add(s)
        return sorted(list(flat))

    def _load_old_profile_raw(self) -> CandidateProfile | None:
        """Attempt to load the old profile JSON directly from file if it exists."""
        profile_file = self.cache_dir / "candidate_profile.json"
        if profile_file.exists():
            try:
                data = json.loads(profile_file.read_text(encoding="utf-8"))
                return CandidateProfile.model_validate(data)
            except Exception as exc:
                logger.warning(f"Could not load old profile for change comparison: {exc}")
        return None
