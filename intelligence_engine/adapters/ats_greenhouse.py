from typing import List
from datetime import datetime
import uuid
from intelligence_engine.adapters.base import BaseAdapter
from job_model.universal_model import UniversalJobModel, JobInfoModel, CompanyModel, ApplicationModel, IdentityModel

class GreenhouseAdapter(BaseAdapter):
    """Adapter for Greenhouse ATS."""

    def __init__(self):
        super().__init__("Greenhouse ATS", "Official ATS")

    def retrieve(self, company_name: str, base_url: str, keywords: List[str], location: str) -> List[UniversalJobModel]:
        # Mock retrieval from Greenhouse API
        # E.g. https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
        jobs = []
        for kw in keywords[:2]:  # return max 2 jobs based on keywords
            # Mock job structure
            job_id = str(uuid.uuid4())
            model = UniversalJobModel(
                identity=IdentityModel(
                    job_id=job_id,
                    uuid=job_id,
                    source_id=f"GH-{job_id[:8]}",
                    fingerprint=f"{company_name}-{kw}-{location}".lower().replace(" ", "-")
                ),
                job=JobInfoModel(
                    job_title=kw,
                    description=f"We are looking for a {kw} to join {company_name} using Greenhouse.",
                    employment_type="Full-Time",
                    experience_required="Entry Level",
                    salary="Competitive",
                    technologies=["Python", "Machine Learning"],
                    skills=["AI", "Backend"]
                ),
                company=CompanyModel(
                    company_name=company_name,
                    industry="Technology",
                    company_url=base_url
                ),
                application=ApplicationModel(
                    application_url=f"https://boards.greenhouse.io/{company_name.lower().replace(' ', '')}/jobs/{job_id}",
                    is_active=True,
                    posting_date=datetime.utcnow().isoformat(),
                    source="Greenhouse ATS",
                    source_type="Official ATS"
                )
            )
            # Default location init requires manual assignment to nested models if not fully defined in constructor
            model.location.location = location
            jobs.append(model)
        return jobs
