"""
filters/stages/location_priority.py — Stage 8 Location Priority Filter
======================================================================
Purpose
-------
Enforce location targeting constraints and priorities.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class LocationPriorityFilter(BaseFilter):
    """
    Stage 8: Location filtering and priority matching.
    """

    filter_name = "LocationPriority"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        preferred_locations = self.config.get("preferred_locations", [])

        for job in jobs:
            rejections = []
            country = str(job.location.country or "").lower()
            city = str(job.location.city or "").lower()
            remote = job.location.remote

            # Check if international
            if country != "india" and country != "remote" and country != "":
                # International is only allowed if remote
                if not remote:
                    rejections.append(f"Non-India onsite/hybrid location: '{job.location.location}'")
                else:
                    # Remote international must allow Indian candidates
                    desc = job.job.job_description.lower()
                    allowed = any(term in desc for term in ["india", "global", "worldwide", "anywhere", "south asia"])
                    if not allowed:
                        rejections.append("International remote job but no explicit mention of India eligibility")

            # Check if matching any preferred cities
            if not remote and country == "india":
                matched = any(p.lower() in city for p in preferred_locations)
                if not matched:
                    # Allow other Indian cities as lower priority but do not reject unless strict is set
                    # Let's allow it as lowest priority per prompt rules ("Other Indian cities")
                    pass

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
