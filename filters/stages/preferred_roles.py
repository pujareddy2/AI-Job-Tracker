"""
filters/stages/preferred_roles.py — Stage 5 Preferred Roles Filter
==================================================================
Purpose
-------
Match job titles against target roles list.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class PreferredRolesFilter(BaseFilter):
    """
    Stage 5: Job role category matching.
    """

    filter_name = "PreferredRoles"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        target_roles = self.config.get("target_roles", [])

        for job in jobs:
            rejections = []
            title = job.job.job_title.lower()
            desc = job.job.job_description.lower()

            # 1. Direct or general category check
            matches = any(role.lower() in title for role in target_roles)
            if not matches:
                general_ai = any(term in title for term in ["ai ", " ai", "intelligence", "learning", "llm", "gpt"])
                general_backend = "backend" in title or "python" in title
                if not (general_ai or general_backend):
                    rejections.append(f"Role title '{job.job.job_title}' does not match preferred target roles")

            # 2. Reject frontend-only
            is_frontend_title = any(term in title for term in ["frontend", "front-end", "ui ", "react", "angular", "vue", "css", "web developer"])
            has_ai_backend_context = any(term in title or term in desc for term in ["ai ", " ai", "backend", "python", "machine learning", "deep learning", "llm", "rag"])
            if is_frontend_title and not has_ai_backend_context:
                rejections.append("Frontend-only role does not align with candidate profile")

            # 3. Reject Java-only backend
            is_java_title = any(term in title for term in ["java", "spring boot", "springboot", "j2ee"])
            has_python_ai = any(term in title or term in desc for term in ["python", "ai ", " ai", "machine learning", "llm", "fastapi"])
            if is_java_title and not has_python_ai:
                rejections.append("Java-only backend role does not align with candidate profile")

            # 4. Reject DSA-heavy SDE roles
            is_sde_title = "sde" in title or "software development engineer" in title or "software engineer" in title
            is_dsa_heavy = any(term in desc for term in ["data structures and algorithms", "competitive programming", "dsa", "leetcode"])
            if is_sde_title and is_dsa_heavy and not has_python_ai:
                rejections.append("DSA-heavy SDE role without AI/Python focus does not align with candidate profile")

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
