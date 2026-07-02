"""
resume_parser/__init__.py
--------------------------
Makes `resume_parser` a Python package and exposes the public API.

Imports exposed here allow callers to write:
    from resume_parser import ProfileBuilder, CandidateProfile

instead of importing from sub-modules directly.
"""

from __future__ import annotations

from resume_parser.parser import ResumeParser
from resume_parser.profile_model import CandidateProfile, ProfileMeta, InferredRole
from resume_parser.profile_builder import ProfileBuilder
from resume_parser.detector import ResumeDetector
from resume_parser.extractor import ResumeExtractor
from resume_parser.section_parser import SectionParser
from resume_parser.skill_expander import SkillExpander
from resume_parser.inference_engine import InferenceEngine
from resume_parser.keyword_generator import KeywordGenerator
from resume_parser.query_generator import QueryGenerator
from resume_parser.scorer import CandidateScorer
from resume_parser.cache_manager import CacheManager

__all__ = [
    "ResumeParser",
    "CandidateProfile",
    "ProfileMeta",
    "InferredRole",
    "ProfileBuilder",
    "ResumeDetector",
    "ResumeExtractor",
    "SectionParser",
    "SkillExpander",
    "InferenceEngine",
    "KeywordGenerator",
    "QueryGenerator",
    "CandidateScorer",
    "CacheManager",
]
