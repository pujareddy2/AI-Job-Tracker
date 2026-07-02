"""
communication_engine/__init__.py — AI Communication Engine Entry Point
=======================================================================
Purpose
-------
Exposes the main orchestrator (CommunicationEngine) and data schemas.
"""

from __future__ import annotations

from communication_engine.engine import CommunicationEngine

__all__ = ["CommunicationEngine"]
