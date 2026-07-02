"""
utils/checkpoint.py — Checkpoint and State Management
======================================================
Purpose
-------
Manages the pipeline execution state. Allows the orchestrator to resume
from the last successful stage if a transient failure occurs.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineStage(str, Enum):
    """Enumeration of all pipeline stages in order of execution."""
    VALIDATION = "validation"
    RESUME_PARSING = "resume_parsing"
    JOB_DISCOVERY = "job_discovery"
    NORMALIZATION = "normalization"
    FILTERING = "filtering"
    MATCHING = "matching"
    DEDUPLICATION = "deduplication"
    SHEETS_SYNC = "sheets_sync"
    NOTIFICATIONS = "notifications"
    COMPLETED = "completed"


class CheckpointManager:
    """Manages reading and writing pipeline state to disk."""

    def __init__(self, checkpoint_file: str | Path = "cache/checkpoint.json") -> None:
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        """Load the current checkpoint state."""
        if not self.checkpoint_file.exists():
            return self._default_state()
        try:
            content = self.checkpoint_file.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as exc:
            logger.warning(f"Failed to load checkpoint file, starting fresh: {exc}")
            return self._default_state()

    def save_state(self, stage: PipelineStage, data: dict[str, Any] | None = None) -> None:
        """Save the successful completion of a stage."""
        state = self.load_state()
        state["last_completed_stage"] = stage.value
        state["timestamp"] = datetime.now().isoformat()
        if data:
            state["data"].update(data)
        
        try:
            self.checkpoint_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
            logger.debug(f"Checkpoint saved: {stage.value}")
        except Exception as exc:
            logger.error(f"Failed to save checkpoint: {exc}")

    def clear(self) -> None:
        """Clear the checkpoint file to force a fresh run."""
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                logger.info("Cleared previous pipeline checkpoint.")
            except Exception as exc:
                logger.warning(f"Could not clear checkpoint: {exc}")

    def is_completed(self, stage: PipelineStage) -> bool:
        """Check if a specific stage has already been completed in this run."""
        state = self.load_state()
        last_stage = state.get("last_completed_stage")
        if not last_stage:
            return False
            
        stages = list(PipelineStage)
        try:
            current_idx = stages.index(PipelineStage(last_stage))
            target_idx = stages.index(stage)
            return current_idx >= target_idx
        except ValueError:
            return False

    def _default_state(self) -> dict[str, Any]:
        return {
            "last_completed_stage": None,
            "timestamp": None,
            "data": {}
        }
