import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class SourceCategory(str, Enum):
    OFFICIAL_API = "Official API"
    OFFICIAL_ATS = "Official ATS"
    OFFICIAL_CAREER_PAGE = "Official Career Page"
    JOB_BOARD = "Job Board"
    SEARCH_DISCOVERY = "Search Discovery"
    RSS_FEED = "RSS Feed"
    STRUCTURED_DATA = "Structured Data"
    UNIVERSITY_PORTAL = "University Hiring Portal"
    GOVERNMENT_PORTAL = "Government Hiring Portal"
    STARTUP_PORTAL = "Startup Portal"
    COMPANY_CMS = "Company Career CMS"

@dataclass
class SourceHealth:
    name: str
    category: str
    attempted: int = 0
    succeeded: int = 0
    jobs_retrieved: int = 0
    jobs_accepted: int = 0
    jobs_rejected: int = 0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    average_response_time: float = 0.0
    reliability_score: float = 100.0
    failure_reason: Optional[str] = None

class SourceIntelligence:
    """Manages source categories and tracks health metrics."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or settings.cache_dir / "source_health.json"
        self.sources: Dict[str, SourceHealth] = {}
        self.load()

    def load(self) -> None:
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self.sources[k] = SourceHealth(**v)
            except Exception as e:
                logger.error(f"Failed to load source health: {e}")

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: asdict(v) for k, v in self.sources.items()}
            self.cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save source health: {e}")

    def get_or_create(self, name: str, category: SourceCategory) -> SourceHealth:
        if name not in self.sources:
            self.sources[name] = SourceHealth(name=name, category=category.value)
        return self.sources[name]

    def record_attempt(self, name: str) -> None:
        if name in self.sources:
            self.sources[name].attempted += 1
            self.save()

    def record_success(self, name: str, jobs_retrieved: int, jobs_accepted: int, jobs_rejected: int, response_time: float) -> None:
        if name in self.sources:
            from datetime import datetime
            source = self.sources[name]
            source.succeeded += 1
            source.jobs_retrieved += jobs_retrieved
            source.jobs_accepted += jobs_accepted
            source.jobs_rejected += jobs_rejected
            source.last_success = datetime.utcnow().isoformat()
            
            # EMA for response time
            if source.average_response_time == 0.0:
                source.average_response_time = response_time
            else:
                source.average_response_time = (source.average_response_time * 0.8) + (response_time * 0.2)
            
            source.reliability_score = min(100.0, source.reliability_score + 1.0)
            self.save()

    def record_failure(self, name: str, reason: str) -> None:
        if name in self.sources:
            from datetime import datetime
            source = self.sources[name]
            source.last_failure = datetime.utcnow().isoformat()
            source.failure_reason = reason
            source.reliability_score = max(0.0, source.reliability_score - 15.0)
            self.save()

    def generate_discovery_report(self) -> str:
        """Generates a text report of source health after a run."""
        lines = []
        lines.append("=" * 80)
        lines.append("JOB DISCOVERY ENGINE — SOURCE HEALTH REPORT")
        lines.append("=" * 80)
        lines.append(f"{'Source Name':<25} | {'Type':<20} | {'Att':<4} | {'Succ':<4} | {'Jobs':<4} | {'Acc':<4} | {'Rej':<4} | {'Reliability':<11} | {'Status'}")
        lines.append("-" * 80)
        for s in sorted(self.sources.values(), key=lambda x: x.reliability_score, reverse=True):
            status = "FAIL: " + str(s.failure_reason) if s.failure_reason and (s.reliability_score < 100 or s.succeeded == 0) else "OK"
            # Truncate status if needed
            if len(status) > 20: status = status[:17] + "..."
            lines.append(f"{s.name:<25} | {s.category:<20} | {s.attempted:<4} | {s.succeeded:<4} | {s.jobs_retrieved:<4} | {s.jobs_accepted:<4} | {s.jobs_rejected:<4} | {s.reliability_score:>9.1f}% | {status}")
        lines.append("=" * 80)
        return "\n".join(lines)
