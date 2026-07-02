"""
tests/test_inference_engine.py — Unit Tests for resume_parser/inference_engine.py
================================================================================
Tests verify (no network, no files required):
  1. High score matched for candidates with both required and optional skills.
  2. Low score matched (or filtered out) when required skills are missing.
  3. Weighted formula calculations for role matching are correct.
  4. Roles sorted descending by score.
"""

from __future__ import annotations

from resume_parser.inference_engine import InferenceEngine, RoleRule


def test_role_rule_score_calculation() -> None:
    # 70% required, 30% optional weight
    rule = RoleRule(
        title="Test Engineer",
        required_skills={"python", "pytest"},
        optional_skills={"docker", "git"}
    )

    # 1. Matches everything (100%)
    res_1 = rule.calculate_score(["Python", "pytest", "Docker", "Git"])
    assert res_1 is not None
    assert res_1.score == 100
    assert "pytest" in res_1.matched_skills

    # 2. Matches required only (70% base, 0% boost)
    res_2 = rule.calculate_score(["Python", "pytest"])
    assert res_2 is not None
    assert res_2.score == 70

    # 3. Matches some required, some optional
    # 1/2 required = 35% base
    # 1/2 optional = 15% boost
    # total = 50%
    res_3 = rule.calculate_score(["Python", "Docker"])
    assert res_3 is not None
    assert res_3.score == 50

    # 4. Under 50% threshold -> returns None
    res_4 = rule.calculate_score(["Docker", "Git"])  # no required match
    assert res_4 is None


def test_inference_engine_outputs() -> None:
    engine = InferenceEngine()
    
    # AI Developer profile
    skills = ["Python", "FastAPI", "LangChain", "ChromaDB", "PostgreSQL", "Docker", "AWS", "RAG", "LLM", "Prompt Engineering"]
    roles = engine.infer(skills)
    
    # Should infer Applied AI Engineer and LLM Engineer at very high scores
    titles = [r.title for r in roles]
    assert "Applied AI Engineer" in titles
    assert "LLM Engineer" in titles
    assert "Python Backend Engineer" in titles

    # The highest scoring role should be first
    assert roles[0].score >= roles[-1].score
