"""
tests/test_skill_expander.py — Unit Tests for resume_parser/skill_expander.py
=============================================================================
Tests verify (no network, no files required):
  1. Expansion of a single known skill (e.g. FastAPI) matches expected terms.
  2. Unrecognized skills default to returning themselves.
  3. Batch expansion maps keys to correct values.
  4. Flat expansion returns a flat, sorted list containing original skill.
"""

from __future__ import annotations

from resume_parser.skill_expander import SkillExpander


def test_expand_known_skill() -> None:
    expander = SkillExpander()
    expansions = expander.expand_skill("FastAPI")
    assert "FastAPI" in expansions
    assert "Python Backend" in expansions
    assert "REST APIs" in expansions


def test_expand_unknown_skill() -> None:
    expander = SkillExpander()
    expansions = expander.expand_skill("SomeNewTechXYZ")
    assert expansions == ["SomeNewTechXYZ"]


def test_batch_expansion() -> None:
    expander = SkillExpander()
    results = expander.expand(["Python", "LangChain"])
    assert "Python" in results
    assert "LangChain" in results
    assert len(results["Python"]) > 1
    assert len(results["LangChain"]) > 1


def test_flat_expansion_deduplicates_and_sorts() -> None:
    expander = SkillExpander()
    flat = expander.get_flat_expansions(["FastAPI", "FastAPI"])  # double input
    assert len(flat) == len(set(flat))
    assert "FastAPI" in flat
    assert "Python Backend" in flat
