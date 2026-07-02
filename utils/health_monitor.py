"""
utils/health_monitor.py — Pipeline Health and Performance Tracking
==================================================================
Purpose
-------
Tracks the overall health of the pipeline run. Gathers statistics
from each stage (execution time, job counts, memory usage if possible)
and generates a final health report for debugging and observability.
"""

from __future__ import annotations

import json
import time
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


class HealthMonitor:
    """Monitors performance and generates a health report."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.pipeline_version = "3.0.0"
        self.resume_hash = ""
        self.stages_data: dict[str, Any] = {}
        self.errors: list[dict[str, Any]] = []
        self.metrics: dict[str, int | float] = {
            "jobs_discovered": 0,
            "jobs_normalized": 0,
            "jobs_filtered": 0,
            "jobs_matched": 0,
            "jobs_deduplicated": 0,
            "sheets_updated": 0,
            "emails_sent": 0
        }
        self.process = psutil.Process(os.getpid())

    def start_stage(self, stage_name: str) -> None:
        """Mark the beginning of a pipeline stage."""
        self.stages_data[stage_name] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "status": "running"
        }

    def end_stage(self, stage_name: str, status: str = "success") -> None:
        """Mark the end of a pipeline stage and calculate its duration."""
        if stage_name in self.stages_data:
            stage = self.stages_data[stage_name]
            stage["end_time"] = time.time()
            stage["duration"] = stage["end_time"] - stage["start_time"]
            stage["status"] = status

    def record_error(self, stage_name: str, error_type: str, message: str) -> None:
        """Record an error that occurred during execution."""
        self.errors.append({
            "stage": stage_name,
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        self.end_stage(stage_name, status="failed")

    def update_metrics(self, **kwargs: int | float) -> None:
        """Update job volume metrics."""
        self.metrics.update(kwargs)

    def generate_report(self) -> dict[str, Any]:
        """Compile the final health report."""
        total_duration = time.time() - self.start_time
        
        # Format stage durations
        formatted_stages = {}
        for name, data in self.stages_data.items():
            duration = data.get("duration")
            formatted_stages[name] = {
                "duration_seconds": round(duration, 2) if duration else None,
                "status": data.get("status")
            }

        # Memory usage (RSS in MB)
        memory_mb = self.process.memory_info().rss / (1024 * 1024)

        report = {
            "pipeline_version": self.pipeline_version,
            "resume_hash": self.resume_hash,
            "execution_date": datetime.now().isoformat(),
            "total_duration_seconds": round(total_duration, 2),
            "memory_usage_mb": round(memory_mb, 2),
            "overall_status": "failed" if self.errors else "success",
            "metrics": self.metrics,
            "stages": formatted_stages,
            "errors": self.errors
        }
        return report

    def save_report(self, path: str | Path = "cache/health_report.json") -> None:
        """Save the generated health report to disk."""
        try:
            report_path = Path(path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(self.generate_report(), indent=2), encoding="utf-8")
            logger.info(f"Health report saved to {path}")
        except Exception as exc:
            logger.error(f"Failed to save health report: {exc}")
