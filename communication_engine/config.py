"""
communication_engine/config.py — Configuration for the AI Communication Engine
=============================================================================
Purpose
-------
Centralized options, weights, paths, and metadata settings for document generation.

Design Decisions
----------------
- Immutable-friendly configuration parameters.
- Configurable quality weights that sum to 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class QualityWeights:
    """Weights for the 6 document quality metrics (sums to 1.0)."""
    readability: float = 0.15
    professionalism: float = 0.20
    personalization: float = 0.25
    truthfulness: float = 0.20
    grammar: float = 0.10
    completeness: float = 0.10

    def validate(self) -> None:
        total = sum([
            self.readability, self.professionalism, self.personalization,
            self.truthfulness, self.grammar, self.completeness
        ])
        assert abs(total - 1.0) < 0.001, f"Quality weights must sum to 1.0, got {total}"


@dataclass
class CommunicationConfig:
    """Master configuration settings for the AI Communication Engine."""
    default_tone: str = "Professional"
    default_export_formats: list[str] = field(
        default_factory=lambda: ["txt", "md", "docx", "pdf", "html"]
    )
    quality_weights: QualityWeights = field(default_factory=QualityWeights)
    output_dir: str = "cache/communication"

    def __post_init__(self) -> None:
        self.quality_weights.validate()


# Global default configuration instance
DEFAULT_COMMUNICATION_CONFIG = CommunicationConfig()
