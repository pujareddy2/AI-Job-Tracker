from typing import List
from datetime import datetime
import uuid
from intelligence_engine.adapters.base import BaseAdapter
from job_model.universal_model import UniversalJobModel, JobInfoModel, CompanyModel, ApplicationModel, IdentityModel

class LeverAdapter(BaseAdapter):
    """Adapter for Lever ATS."""

    def __init__(self):
        super().__init__("Lever ATS", "Official ATS")

    def retrieve(self, company_name: str, base_url: str, keywords: List[str], location: str) -> List[UniversalJobModel]:
        # Mock retrieval from Lever API
        jobs = []
        for kw in keywords[:2]:
            job_id = str(uuid.uuid4())
            model = UniversalJobModel(
                identity=IdentityModel(
                    job_id=job_id,
                    uuid=job_id,
                    source_id=f"LEV-{job_id[:8]}",
                    fingerprint=f"{company_name}-{kw}-{location}".lower().replace(" ", "-")
                ),
                job=JobInfoModel(
                    job_title=kw,
                    description=f"Leverage your skills as a {kw} at {company_name}.",
                    employment_type="Full-Time",
                    experience_required="Early Career",
                    salary="Competitive",
                    technologies=["Python", "Go"],
                    skills=["AI", "Backend"]
                ),
                company=CompanyModel(
                    company_name=company_name,
                    industry="Technology",
                    company_url=base_url
                ),
                application=ApplicationModel(
                    application_url=f"https://jobs.lever.co/{company_name.lower().replace(' ', '')}/{job_id}",
                    is_active=True,
                    posting_date=datetime.utcnow().isoformat(),
                    source="Lever ATS",
                    source_type="Official ATS"
                )
            )
            model.location.location = location
            jobs.append(model)
        return jobs
