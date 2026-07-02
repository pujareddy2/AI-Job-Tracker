"""
resume_optimizer/__init__.py — Public API for the Resume Optimization Engine
=============================================================================
Purpose
-------
Expose the primary entry point so callers only need to import from this
package root rather than from individual sub-modules.

Usage
-----
    from resume_optimizer import ResumeOptimizationEngine
    from resume_optimizer.models import PerJobOptimizationReport, CareerSummaryReport
"""

from __future__ import annotations

from resume_optimizer.engine import ResumeOptimizationEngine

__all__ = ["ResumeOptimizationEngine"]
