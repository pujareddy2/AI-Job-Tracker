# docs/job_discovery.md — Job Discovery Engine Documentation

This document describes the design, architecture, configuration, and modules
of the Multi-Source Job Discovery Engine (Phase 4).

---

## Architecture

The Job Discovery Engine acts as the primary acquisition portal for job opportunities.
It isolates 30 distinct job boards, aggregators, and career portals into modular,
independent scrapers inheriting from a common base interface.

```
                    +------------------------------------+
                    |     Candidate Profile Cache        | (cache/candidate_profile.json)
                    +-----------------+------------------+
                                      |
                                      | Reads keywords/location
                                      ▼
                    +------------------------------------+
                    |        JobDiscoveryEngine          |
                    +-----------------+------------------+
                                      |
                        Schedules scraper runs
                                      ▼
            +-------------------------+-------------------------+
            |                         |                         |
            ▼                         ▼                         ▼
   +------------------+      +------------------+      +------------------+
   | Priority Tier 1  |      | Priority Tier 2  |      | Priority Tier 3  |
   +--------+---------+      +--------+---------+      +--------+---------+
            |                         |                         |
            | Runs parallel           | Runs parallel           | Runs if Tier 1 & 2
            |                         |                         | completed without
            |                         |                         | fatal crash
            ▼                         ▼                         ▼
     - Company Careers         - Naukri                  - HackerRank
     - LinkedIn Jobs           - Foundit                 - Shine
     - Wellfound               - Cutshort                - Apna
     - YC Jobs                 - Instahyre               - RemoteOK
     - Google/Microsoft        - Indeed India            - Dynamic Discovery
            |                         |                         |
            +-------------------------+-------------------------+
                                      |
                                      ▼
                    +------------------------------------+
                    |      Standard Output Model         | (Pydantic validation)
                    +-----------------+------------------+
                                      |
                                      ▼
                    +------------------------------------+
                    |      Discovered Jobs Cache         | (cache/discovered_jobs.json)
                    +------------------------------------+
```

---

## Module Responsibilities

Every job source has its own isolated python file in `scrapers/`. This ensures
decoupled development: you can refactor or replace a scraper for one website
without risking side-effects in another scraper.

### Priority Tiers

| Tier | Purpose | Sources |
|---|---|---|
| **Tier 1 (Highest)** | Direct career portals and high-fidelity tech boards. High trust. | Company Careers, LinkedIn, Wellfound, Work at a Startup, YC Jobs, Hugging Face, Google, Microsoft, Amazon, NVIDIA |
| **Tier 2 (Medium)** | General job boards and aggregators in India. Large volume. | Naukri, Foundit, Cutshort, Hirist, Instahyre, Indeed India, Freshersworld, Internshala, Unstop, HackerEarth |
| **Tier 3 (Low)** | Niche tech boards, dynamic web crawlers, and fallback portals. | HackerRank, TimesJobs, Shine, Apna, PlacementIndia, FreshersNow, OffCampusJobs4U, RemoteOK, Dynamic Startup Discovery, AI Startup Google Search |

---

## Standard Output Model

Every scraper translates raw HTML tables or API JSONs into a list of unified
Pydantic `JobOpportunity` objects:

```json
{
  "company": "TechCorp Solutions",
  "role": "Applied AI Engineer",
  "location": "Hyderabad",
  "employment_type": "Full-time",
  "experience": "0-1 Years",
  "graduation_eligibility": "2026/2027 Batch",
  "internship_or_full_time": "Internship",
  "ppo_mentioned": true,
  "salary": "12 LPA",
  "remote_status": "On-site",
  "application_url": "https://linkedin.com/jobs/techcorp-applied-ai-engineer-0",
  "company_careers_url": "https://www.techcorp.com/careers",
  "job_description": "Join the TechCorp team building next-generation AI solutions...",
  "posting_date": "2026-06-28",
  "platform": "LinkedIn",
  "source_reliability_score": 98,
  "verified_status": true,
  "timestamp": "2026-06-28T11:40:00.000000",
  "job_id": "sha256:abc123xyz..."
}
```

### Job ID Generation

To ensure unique identification across platforms and execution cycles, we compute a deterministic hash:

$$\text{job\_id} = \text{SHA-256}(\text{platform} + \text{company} + \text{role} + \text{location} + \text{application\_url} + \text{posting\_date})$$

Duplicate checks and database merges will utilize this key in subsequent phases.

---

## Trust and Reliability Scoring

Each source is assigned a trust rating based on application accessibility, job posting freshness, and historical verification rates:

- **100**: Direct Company Career Portals (Google, Microsoft, Amazon, NVIDIA, Company Careers) - guaranteed genuine openings.
- **98**: LinkedIn - highly verified postings with active apply channels.
- **96-97**: Specialized startup hubs (Wellfound, Work at a Startup, YC Jobs).
- **88-92**: Large regional aggregators (Naukri, Instahyre, Foundit).
- **80-85**: General job search engines (Indeed, Internshala, Unstop).
- **70-76**: Low-fidelity aggregators and generic crawlers (Apna, PlacementIndia, Shine).

---

## How to Add a New Source

Adding a new source is extremely simple:

1. Create a new python file in `scrapers/` (e.g. `scrapers/glassdoor.py`).
2. Implement a class inheriting from `BaseScraper`:
   ```python
   from scrapers.base_scraper import BaseScraper
   from scrapers.models import JobOpportunity
   
   class GlassdoorScraper(BaseScraper):
       source_name = "Glassdoor"
       base_url = "https://www.glassdoor.com"
       reliability_score = 90
       
       def validate_config(self) -> None:
           pass
           
       def scrape(self, keyword: str, location: str, **kwargs) -> list[JobOpportunity]:
           # 1. Fetch search HTML/API
           # 2. Parse and normalize rows
           # 3. Return standard JobOpportunity list
           return []
   ```
3. Register the scraper in `scrapers/discovery_engine.py` inside the appropriate tier list.
