"""
observability_engine/tracker.py
===============================
Tracks state, timings, memory usage, and collects metrics for all pipeline stages.
Replaces the basic HealthMonitor.
"""

from __future__ import annotations
import time
import psutil
import os
import uuid
from datetime import datetime
from collections import defaultdict
from typing import Any

from observability_engine.models import (
    PipelineReport,
    StageMetrics,
    SourceMetrics,
    RejectionRecord,
    RejectionAnalytics,
    ConfidenceMetrics,
    ResumeMatchMetrics,
    ATSMetrics,
    SheetsMetrics,
    NotionMetrics,
    EmailMetrics,
    PipelineHealthScore
)
from job_model.universal_model import UniversalJobModel
from utils.logger import get_logger

logger = get_logger(__name__)


class ObservabilityTracker:
    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())
        
        self.stages: dict[str, StageMetrics] = {}
        self._stage_start_times: dict[str, float] = {}
        
        self.sources: dict[str, SourceMetrics] = {}
        self.rejected_jobs: list[RejectionRecord] = []
        self.accepted_jobs: list[UniversalJobModel] = []
        
        self.rejection_analytics = RejectionAnalytics()
        self.confidence_metrics = ConfidenceMetrics()
        self.resume_match_metrics = ResumeMatchMetrics()
        self.ats_metrics = ATSMetrics()
        self.sheets_metrics = SheetsMetrics()
        self.notion_metrics = NotionMetrics()
        self.email_metrics = EmailMetrics()
        self.health_score = PipelineHealthScore()
        self.recommendations: list[str] = []
        
        # Backwards compatibility attributes
        self.resume_hash = ""
        self._metrics: dict[str, int | float] = {}
        self.errors: list[dict[str, Any]] = []

    def start_stage(self, stage_name: str) -> None:
        self._stage_start_times[stage_name] = time.time()
        if stage_name not in self.stages:
            self.stages[stage_name] = StageMetrics(stage_name=stage_name)
        logger.debug(f"[Observability] Started tracking stage: {stage_name}")

    def end_stage(self, stage_name: str, status: str = "success", input_jobs: int = 0, output_jobs: int = 0, errors: int = 0, warnings: int = 0, retry_count: int = 0) -> None:
        if stage_name not in self._stage_start_times:
            return
            
        execution_time = time.time() - self._stage_start_times[stage_name]
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        
        stage = self.stages[stage_name]
        stage.execution_time_seconds = execution_time
        stage.input_jobs = input_jobs
        stage.output_jobs = output_jobs
        stage.rejected_jobs = max(0, input_jobs - output_jobs)
        stage.errors += errors if status != "failed" else 1
        stage.warnings += warnings
        stage.retry_count += retry_count
        stage.memory_usage_mb = memory_mb
        
        if input_jobs > 0:
            stage.average_processing_time_ms = (execution_time * 1000) / input_jobs
            stage.success_rate = (output_jobs / input_jobs) * 100
            stage.failure_rate = (stage.rejected_jobs / input_jobs) * 100
            
        logger.debug(f"[Observability] Ended tracking stage: {stage_name} (took {execution_time:.2f}s)")

    def record_rejection(self, job: UniversalJobModel, stage: str, reason: str) -> None:
        """Records a job rejection with full context."""
        record = RejectionRecord(
            company=job.company.company_name,
            role=job.job.job_title,
            url=job.application.application_url,
            source=job.application.platform,
            pipeline_stage=stage,
            exact_reason=reason,
            timestamp=datetime.now().isoformat(),
            confidence_before_rejection=job.confidence.overall_score,
            resume_match_score=job.confidence.resume_match_score,
            ats_score=job.confidence.ats_match_score,
            technology_match_score=job.confidence.technology_match_score,
            experience_score=job.confidence.experience_match_score,
            location_score=job.confidence.location_match_score,
            trust_score=job.confidence.trust_score,
            graduation_score=job.confidence.graduation_score
        )
        self.rejected_jobs.append(record)

    def record_source_metric(self, metric: SourceMetrics) -> None:
        self.sources[metric.source_name] = metric

    def compute_analytics(self) -> None:
        # Rejection analytics
        reasons_count = defaultdict(int)
        for r in self.rejected_jobs:
            reasons_count[r.exact_reason] += 1
            
        total_rejections = len(self.rejected_jobs)
        percentages = {}
        if total_rejections > 0:
            for reason, count in reasons_count.items():
                percentages[reason] = round((count / total_rejections) * 100, 2)
                
        self.rejection_analytics = RejectionAnalytics(
            rejection_reasons=dict(reasons_count),
            rejection_percentages=percentages
        )
        
        # Pipeline Health Score calculation
        for stage in self.stages.values():
            if stage.stage_name == "Job Discovery Engine":
                self.health_score.discovery_health = stage.success_rate
            elif stage.stage_name == "Job Filtering Engine":
                self.health_score.filtering_health = 100.0 if stage.errors == 0 else 0.0
                
        # Overall health
        self.health_score.overall_pipeline_health = (
            self.health_score.discovery_health +
            self.health_score.filtering_health +
            self.health_score.matching_health +
            self.health_score.google_health +
            self.health_score.email_health
        ) / 5.0

    def generate_report(self) -> PipelineReport:
        self.compute_analytics()
        return PipelineReport(
            run_id=self.run_id,
            execution_date=datetime.now().isoformat(),
            total_execution_time_seconds=time.time() - self.start_time,
            stages=self.stages,
            sources=self.sources,
            rejected_jobs=self.rejected_jobs,
            rejection_analytics=self.rejection_analytics,
            confidence_metrics=self.confidence_metrics,
            resume_match_metrics=self.resume_match_metrics,
            ats_metrics=self.ats_metrics,
            sheets_metrics=self.sheets_metrics,
            notion_metrics=self.notion_metrics,
            email_metrics=self.email_metrics,
            health_score=self.health_score,
            recommendations=self.recommendations
        )

    # --- Backwards Compatibility Methods for HealthMonitor ---
    
    def record_error(self, stage_name: str, error_type: str, message: str) -> None:
        self.errors.append({
            "stage": stage_name,
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        self.end_stage(stage_name, status="failed")
        
    def update_metrics(self, **kwargs: int | float) -> None:
        self._metrics.update(kwargs)
        
    def save_report(self, path: Path) -> None:
        from observability_engine.reporters import ReportGenerator
        from observability_engine.recommender import Recommender
        
        report = self.generate_report()
        report.recommendations = Recommender.generate_recommendations(report)
        
        # We output to the same directory as the requested path
        out_dir = path.parent / "observability"
        reporter = ReportGenerator(out_dir)
        reporter.generate_json_reports(report, self.accepted_jobs)
        reporter.generate_html_dashboard(report)
        logger.info(f"Observability reports saved to {out_dir}")
