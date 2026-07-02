"""
filters/base_filter.py — Abstract Base Class for All Filters
============================================================
Purpose
-------
Define the interface that every filter (rule-based or AI-powered) must
implement.  This enforces consistency and allows the pipeline to chain
filters together without knowing their internal logic.

Responsibilities
----------------
- Define abstract `filter()` method that takes a list of job dicts and
  returns the subset that passes the filter's criteria.
- Optionally define `score()` for filters that rank jobs numerically.
- Provide a `name` property for logging and pipeline reporting.

Concrete filters (Phase 3+)
----------------------------
    filters/keyword_filter.py   → KeywordFilter (rule-based)
    filters/salary_filter.py    → SalaryFilter  (rule-based)
    filters/ai_filter.py        → AIRelevanceFilter (LLM-powered)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from job_model.universal_model import UniversalJobModel
from utils.logger import get_logger


class BaseFilter(ABC):
    """
    Abstract base class for all job filters.
    """

    filter_name: str = "BaseFilter"

    def __init__(self, rules_config: dict[str, Any] | None = None) -> None:
        self.logger = get_logger(f"filters.{self.filter_name.lower()}")
        self.config = rules_config or {}

    @abstractmethod
    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        """
        Filter a list of job models.

        Parameters
        ----------
        jobs : list[UniversalJobModel]
            Input standard job models.

        Returns
        -------
        list[UniversalJobModel]
            Subset of jobs that satisfy this filter's criteria.
        """

    def score(self, job: UniversalJobModel) -> float:
        """
        Assign a relevance score (0.0–1.0) to a single job.
        """
        return 1.0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.filter_name!r}>"
