from typing import List
from datetime import datetime
import uuid
from intelligence_engine.adapters.base import BaseAdapter
from job_model.universal_model import UniversalJobModel, JobInfoModel, CompanyModel, ApplicationModel, IdentityModel

class WorkdayAdapter(BaseAdapter):
    """Adapter for Workday ATS."""

    def __init__(self):
        super().__init__("Workday ATS", "Official ATS")

    def retrieve(self, company_name: str, base_url: str, keywords: List[str], location: str) -> List[UniversalJobModel]:
        # Mock retrieval from Workday
        jobs = []
        for kw in keywords[:2]:
            job_id = str(uuid.uuid4())
            model = UniversalJobModel(
                identity=IdentityModel(
                    job_id=job_id,
                    uuid=job_id,
                    source_id=f"WD-{job_id[:8]}",
                    fingerprint=f"{company_name}-{kw}-{location}".lower().replace(" ", "-")
                ),
                job=JobInfoModel(
                    job_title=kw,
                    description=f"Join {company_name} as a {kw}. Apply via Workday.",
                    employment_type="Full-Time",
                    experience_required="Recent Graduate",
                    salary="Competitive",
                    technologies=["Python", "Cloud"],
                    skills=["AI", "Backend"]
                ),
                company=CompanyModel(
                    company_name=company_name,
                    industry="Enterprise",
                    company_url=base_url
                ),
                application=ApplicationModel(
                    application_url=f"https://myworkdayjobs.com/{company_name.lower().replace(' ', '')}/job/{job_id}",
                    is_active=True,
                    posting_date=datetime.utcnow().isoformat(),
                    source="Workday ATS",
                    source_type="Official ATS"
                )
            )
            model.location.location = location
            jobs.append(model)
        return jobs
