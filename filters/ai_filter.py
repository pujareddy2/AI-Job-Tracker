"""
filters/ai_filter.py — AI-Powered Relevance Filter (Stub)
=========================================================
Purpose
-------
Use a Large Language Model (LLM) to score each job listing for
relevance against the user's resume and preferences.

Phase 1: Stub only.

Responsibilities (Phase 3+)
----------------------------
- Load the parsed resume data from resume_parser output.
- Construct a structured prompt containing the job description and
  key resume facts (skills, target roles, experience level).
- Call an LLM API (OpenAI / Gemini / local Ollama) and parse the
  returned relevance score and reasoning text.
- Attach `ai_score` and `ai_reasoning` fields to each job dict.
- Filter out jobs below a configurable score threshold.
"""

from __future__ import annotations

from typing import Any

from filters.base_filter import BaseFilter


class AIRelevanceFilter(BaseFilter):
    """
    LLM-powered job relevance filter.

    Phase 1: Stub — returns all jobs unchanged.
    """

    filter_name: str = "AIRelevanceFilter"

    def filter(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Phase 3: score each job with an LLM and discard low-scoring results.
        Phase 1: pass-through — returns all jobs unmodified.
        """
        self.logger.info(
            "AIRelevanceFilter.filter() called (stub — all jobs passed through)",
            extra={"job_count": len(jobs)},
        )
        # TODO (Phase 3): implement LLM scoring
        return jobs
