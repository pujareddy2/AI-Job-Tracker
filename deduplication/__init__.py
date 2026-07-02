"""
deduplication package
---------------------
Exposes deduplication, normalization, text similarity, and validation engines.
"""

from __future__ import annotations

from deduplication.url_normalizer import URLNormalizer
from deduplication.normalizers import EntityNormalizer
from deduplication.similarity import TextSimilarity
from deduplication.validation import JobDataValidator
from deduplication.dedup_engine import JobDeduplicator

__all__ = [
    "URLNormalizer",
    "EntityNormalizer",
    "TextSimilarity",
    "JobDataValidator",
    "JobDeduplicator",
]
