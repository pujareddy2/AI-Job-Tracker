"""
filters package
---------------
Makes `filters` a Python package and exports the multi-stage filter pipeline.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from filters.pipeline import JobFilteringPipeline

__all__ = [
    "BaseFilter",
    "JobFilteringPipeline",
]
