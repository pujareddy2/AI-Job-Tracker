"""
resume_matcher package
----------------------
Exposes the ResumeMatcher orchestrator, ScoreCalculator, MatchExplainer, and SemanticIntelligence.
"""

from __future__ import annotations

from resume_matcher.semantic_intelligence import SemanticIntelligence
from resume_matcher.scoring import ScoreCalculator
from resume_matcher.explainers import MatchExplainer
from resume_matcher.matcher import ResumeMatcher

__all__ = [
    "SemanticIntelligence",
    "ScoreCalculator",
    "MatchExplainer",
    "ResumeMatcher",
]
