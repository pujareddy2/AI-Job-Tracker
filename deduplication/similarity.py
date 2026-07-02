"""
deduplication/similarity.py — Text Similarity Engine
=====================================================
Purpose
-------
Calculate textual similarity between job descriptions using token overlap
and sequence matching algorithms.
"""

from __future__ import annotations

import difflib
import re


class TextSimilarity:
    """
    Computes description and field similarity metrics.
    """

    # Basic stop words to filter out before comparison
    STOP_WORDS = {
        "and", "the", "for", "with", "a", "an", "to", "in", "of", "our", "we", "are",
        "hiring", "job", "candidate", "role", "position", "team", "join", "requires"
    }

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        """Convert text into cleaned, lowercase word token set."""
        words = re.findall(r"\b\w+\b", text.lower())
        return {w for w in words if w not in cls.STOP_WORDS}

    @classmethod
    def calculate_jaccard_similarity(cls, text_a: str, text_b: str) -> float:
        """
        Calculate Jaccard token overlap similarity.
        """
        tokens_a = cls._tokenize(text_a)
        tokens_b = cls._tokenize(text_b)
        
        if not tokens_a or not tokens_b:
            return 0.0
            
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        
        return len(intersection) / len(union)

    @classmethod
    def calculate_sequence_similarity(cls, text_a: str, text_b: str) -> float:
        """
        Calculate SequenceMatcher ratio similarity.
        """
        if not text_a or not text_b:
            return 0.0
            
        # Limit comparison length to prevent scaling bottlenecks on large descriptions
        clean_a = " ".join(text_a.lower().split()[:200])
        clean_b = " ".join(text_b.lower().split()[:200])
        
        matcher = difflib.SequenceMatcher(None, clean_a, clean_b)
        return matcher.ratio()

    @classmethod
    def get_similarity_score(cls, text_a: str, text_b: str) -> float:
        """
        Combined similarity metric checking tokens first for scalability.
        """
        # 1. Fast Jaccard check
        jaccard = cls.calculate_jaccard_similarity(text_a, text_b)
        if jaccard < 0.25:
            return jaccard  # skip expensive matchers

        # 2. Detailed sequence match
        return cls.calculate_sequence_similarity(text_a, text_b)
