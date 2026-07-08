import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CompanyProfile:
    name: str
    industry: str = "Unknown"
    hiring_platform: str = "Unknown"
    career_url: str = ""
    official_website: str = ""
    last_successful_scan: Optional[str] = None
    last_failure: Optional[str] = None
    supported_retrieval_method: str = "Search Discovery"
    average_jobs: int = 0
    reliability_score: float = 100.0
    status: str = "Active"

class CompanyRegistry:
    """Maintains a database of tracked companies."""
    
    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or settings.cache_dir / "company_registry.json"
        self.companies: Dict[str, CompanyProfile] = {}
        self.load()

    def load(self) -> None:
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self.companies[k] = CompanyProfile(**v)
            except Exception as e:
                logger.error(f"Failed to load company registry: {e}")

    def save(self) -> None:
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: asdict(v) for k, v in self.companies.items()}
            self.registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save company registry: {e}")

    def add_or_update(self, company: CompanyProfile) -> None:
        """Add a new company or update an existing one."""
        key = company.name.lower()
        if key in self.companies:
            existing = self.companies[key]
            # Update non-destructive fields
            if company.career_url: existing.career_url = company.career_url
            if company.official_website: existing.official_website = company.official_website
            if company.hiring_platform != "Unknown": existing.hiring_platform = company.hiring_platform
            if company.supported_retrieval_method != "Search Discovery": existing.supported_retrieval_method = company.supported_retrieval_method
            
            # Keep the rest unchanged or update if we explicitly passed new data
            self.companies[key] = existing
        else:
            self.companies[key] = company
        self.save()

    def get(self, name: str) -> Optional[CompanyProfile]:
        return self.companies.get(name.lower())

    def get_all(self) -> List[CompanyProfile]:
        return list(self.companies.values())

    def record_success(self, name: str, jobs_found: int) -> None:
        company = self.get(name)
        if company:
            from datetime import datetime
            company.last_successful_scan = datetime.utcnow().isoformat()
            company.status = "Active"
            # Exponential moving average for average jobs
            if company.average_jobs == 0:
                company.average_jobs = jobs_found
            else:
                company.average_jobs = int(company.average_jobs * 0.7 + jobs_found * 0.3)
            
            # Boost reliability score slowly
            company.reliability_score = min(100.0, company.reliability_score + 2.0)
            self.save()

    def record_failure(self, name: str, reason: str) -> None:
        company = self.get(name)
        if company:
            from datetime import datetime
            company.last_failure = f"{datetime.utcnow().isoformat()} - {reason}"
            company.reliability_score = max(0.0, company.reliability_score - 10.0)
            if company.reliability_score < 30.0:
                company.status = "Degraded"
            self.save()
