# docs/job_filtering.md — Intelligent Multi-Stage Job Filtering Engine

This document describes the design, pipeline, stages, and integration path
of the Multi-Stage Job Filtering Engine (Phase 6).

---

## Filtering Architecture

Rather than performing simple keyword filtering in a single large loop, the
filtering engine delegates decisions to **11 sequential filtering stages**.
This mimics the process followed by experienced technical recruiters who split screening
into strict, step-by-step validations.

```
[Normalized Listings Cache] (cache/normalized_jobs.json)
              │
              ▼
   Stage 1: Basic Validation
              │
              ▼
   Stage 2: Employment Type Screen
              │
              ▼
   Stage 3: Graduation batch check
              │
              ▼
   Stage 4: Experience Level check
              │
              ▼
   Stage 5: Preferred Roles match
              │
              ▼
   Stage 6: Technology score calculation
              │
              ▼
   Stage 7: Industry Domain filter
              │
              ▼
   Stage 8: Location Priority mapping
              │
              ▼
   Stage 9: Internship conversion rules
              │
              ▼
   Stage 10: Platform trust & duplicate merging
              │
              ▼
   Stage 11: Rule explanation compiler
              │
              ▼
[Filtered High-Quality Opportunities] (cache/filtered_jobs.json)
```

---

## Why Multiple Stages?

1. **Modularity & Scalability**: Each filter stage is isolated in its own file. You can adjust the experience bounds without risk of breaking location filters.
2. **Explainability**: Every stage collects rejection reasons. If a job is filtered, the output lists exactly which rules caused the rejection (e.g. "Experience limit exceeded").
3. **Optimized I/O**: Strict validation occurs first, allowing the engine to filter out poor listings immediately, saving execution overhead for complex tech score calculations later.

---

## Recruiter Decision Analogy

1. **Stage 1 & 2 (Validation)**: A recruiter verifies that the application link works and that it is not a part-time/unpaid contract role.
2. **Stage 3 & 4 (Eligibility Check)**: The candidate's graduation year (2027) is matched against the target batch requirements. Senior roles (lead, manager) are immediately discarded.
3. **Stage 5 & 6 (Skills Fit)**: The recruiter scores the job description against required tech keywords (Python, FastAPI, LangChain).
4. **Stage 8 & 9 (Preference & Safety)**: Checks if the location fits Hyderabad/Remote targets, and marks uncertain internships as "Needs Manual Review" rather than assuming PPO.
5. **Stage 10 (Verification)**: Deduplicates copy-pasted posts across different portals, picking the listing from the most reliable source.

---

## How to Add a New Filter Rule Stage

Adding a new stage is very simple:

1. Create a new file in `filters/stages/` (e.g. `filters/stages/salary_screen.py`).
2. Inherit from `BaseFilter` and implement `filter()`:
   ```python
   from filters.base_filter import BaseFilter
   from job_model.universal_model import UniversalJobModel
   
   class SalaryScreenFilter(BaseFilter):
       filter_name = "SalaryScreen"
       
       def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
           passed = []
           for job in jobs:
               if job.job.salary_min and job.job.salary_min < 6.0:  # limit LPA
                   job.rejection_reasons.append("Salary is below minimum limit")
               else:
                   passed.append(job)
           return passed
   ```
3. Import the new stage in `filters/stages/__init__.py`.
4. Register the stage in `filters/pipeline.py` inside the `stages` list.
5. Add any threshold values to `config/filter_rules.json`.
