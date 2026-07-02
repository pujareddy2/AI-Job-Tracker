"""
scrapers/discovery_engine.py — Job Discovery Orchestration Engine
==================================================================
Purpose
-------
Coordinate the execution of 30 isolated job scraper sources across three
priority tiers, normalize the output, manage parallel thread pools, log
execution metrics, and handle dynamic company discovery.

Design Decisions
----------------
Thread Pool Concurrency:
    - Running 30 scrapers sequentially would take several minutes.
    - We use a `ThreadPoolExecutor` to run scrapes in parallel (bounded by a default
      of 8 worker threads).
    - This maintains low execution latency while keeping resource usage friendly.

Graceful Degradation:
    - If one scraper fails (raises an exception, hits a rate limit, or configuration is invalid),
      we log the error, record the source failure metric, and continue. One bad website
      must not crash the entire automated execution pipeline.

Three Priority Tiers:
    - Tier 1 runs on every invocation (highest priority sites).
    - Tier 2 runs immediately after Tier 1.
    - Tier 3 runs ONLY if Tier 1 and Tier 2 complete without any fatal orchestrator crashes.

Dynamic Company Discovery Cache:
    - Discovered startup websites and career URLs are saved in `cache/discovered_companies.json`
      to avoid duplicate searches and redundant page scraping.
"""

from __future__ import annotations

import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from config import settings
from scrapers.models import JobOpportunity

# Import concrete scrapers
from scrapers.linkedin import LinkedInScraper
from scrapers.indeed import IndeedScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.work_at_a_startup import WorkAtAStartupScraper
from scrapers.yc_jobs import YCJobsScraper
from scrapers.huggingface_jobs import HuggingFaceJobsScraper
from scrapers.google_careers import GoogleCareersScraper
from scrapers.microsoft_careers import MicrosoftCareersScraper
from scrapers.amazon_jobs import AmazonJobsScraper
from scrapers.nvidia_careers import NvidiaCareersScraper
from scrapers.company_careers import CompanyCareersScraper
from scrapers.verified_platforms import VerifiedPlatformsScraper

from scrapers.naukri import NaukriScraper
from scrapers.foundit import FounditScraper
from scrapers.cutshort import CutshortScraper
from scrapers.hirist import HiristScraper
from scrapers.instahyre import InstahyreScraper
from scrapers.freshersworld import FreshersworldScraper
from scrapers.internshala import InternshalaScraper
from scrapers.unstop import UnstopScraper
from scrapers.hackerearth import HackerEarthScraper

from scrapers.hackerrank_jobs import HackerRankJobsScraper
from scrapers.timesjobs import TimesJobsScraper
from scrapers.shine import ShineScraper
from scrapers.apna import ApnaScraper
from scrapers.placement_india import PlacementIndiaScraper
from scrapers.freshers_now import FreshersNowScraper
from scrapers.off_campus_jobs import OffCampusJobsScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.startup_discovery import StartupDiscoveryScraper
from scrapers.ai_startup_google import AIStartupGoogleScraper
from scrapers.himalayas import HimalayasScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.workingnomads import WorkingNomadsScraper

from utils.logger import get_logger

logger = get_logger(__name__)


class JobDiscoveryEngine:
    """
    Orchestrates job scraping across 3 priority tiers and runs dynamic discovery.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or settings.cache_dir
        self.company_cache_file = self.cache_dir / "discovered_companies.json"

        # Instantiate all 30 scrapers
        self.tier1_scrapers = [
            VerifiedPlatformsScraper(), CompanyCareersScraper(), LinkedInScraper(), WellfoundScraper(),
            WorkAtAStartupScraper(), YCJobsScraper(), HuggingFaceJobsScraper(),
            GoogleCareersScraper(), MicrosoftCareersScraper(), AmazonJobsScraper(),
            NvidiaCareersScraper()
        ]

        self.tier2_scrapers = [
            NaukriScraper(), FounditScraper(), CutshortScraper(),
            HiristScraper(), InstahyreScraper(), IndeedScraper(),
            FreshersworldScraper(), InternshalaScraper(), UnstopScraper(),
            HackerEarthScraper()
        ]

        self.tier3_scrapers = [
            HackerRankJobsScraper(), TimesJobsScraper(), ShineScraper(),
            ApnaScraper(), PlacementIndiaScraper(), FreshersNowScraper(),
            OffCampusJobsScraper(), RemoteOKScraper(), StartupDiscoveryScraper(),
            AIStartupGoogleScraper(), HimalayasScraper(), WeWorkRemotelyScraper(),
            WorkingNomadsScraper()
        ]

        if settings.live_scraping_only:
            self._enable_live_only_mode()

    def _enable_live_only_mode(self) -> None:
        """Keep only scrapers that are implemented as live collectors."""
        before = self.tier1_scrapers + self.tier2_scrapers + self.tier3_scrapers
        self.tier1_scrapers = [s for s in self.tier1_scrapers if s.returns_live_data]
        self.tier2_scrapers = [s for s in self.tier2_scrapers if s.returns_live_data]
        self.tier3_scrapers = [s for s in self.tier3_scrapers if s.returns_live_data]
        after = self.tier1_scrapers + self.tier2_scrapers + self.tier3_scrapers
        skipped = [s.source_name for s in before if not s.returns_live_data]
        logger.info(
            "Live scraping mode enabled",
            extra={
                "active_live_sources": [s.source_name for s in after],
                "skipped_non_live_sources": skipped,
            },
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def discover_all_jobs(self, keywords: list[str], location: str) -> list[JobOpportunity]:
        """
        Execute job discovery across all priority tiers and keywords.

        Parameters
        ----------
        keywords : list[str]
            List of keywords to search for.
        location : str
            Target location.

        Returns
        -------
        list[JobOpportunity]
            Flat list of all collected JobOpportunity objects.
        """
        start_time = time.time()
        logger.info(
            "Job discovery execution started",
            extra={"keywords": keywords, "location": location}
        )

        all_collected_jobs: list[JobOpportunity] = []
        tier1_failed = False
        tier2_failed = False

        # ---------------------------------------------------------------------
        # Tier 1 Execution
        # ---------------------------------------------------------------------
        try:
            tier1_jobs = self._run_tier_parallel(self.tier1_scrapers, keywords, location, tier_label="Tier 1")
            all_collected_jobs.extend(tier1_jobs)
        except Exception as exc:
            logger.error("Tier 1 execution failed with a critical error", exc_info=exc)
            tier1_failed = True

        # ---------------------------------------------------------------------
        # Tier 2 Execution
        # ---------------------------------------------------------------------
        try:
            tier2_jobs = self._run_tier_parallel(self.tier2_scrapers, keywords, location, tier_label="Tier 2")
            all_collected_jobs.extend(tier2_jobs)
        except Exception as exc:
            logger.error("Tier 2 execution failed with a critical error", exc_info=exc)
            tier2_failed = True

        # ---------------------------------------------------------------------
        # Tier 3 Execution (Runs only if Tier 1 and 2 completed successfully)
        # ---------------------------------------------------------------------
        if not tier1_failed and not tier2_failed:
            try:
                tier3_jobs = self._run_tier_parallel(self.tier3_scrapers, keywords, location, tier_label="Tier 3")
                all_collected_jobs.extend(tier3_jobs)
            except Exception as exc:
                logger.error("Tier 3 execution failed with a critical error", exc_info=exc)
        else:
            logger.warning("Skipping Tier 3 execution because Tier 1 or Tier 2 encountered fatal orchestrator exceptions.")

        # Run dynamic company discovery to find and cache new startup career pages
        self.discover_new_companies()

        duration = time.time() - start_time
        all_collected_jobs = self._filter_real_job_records(all_collected_jobs)
        logger.info(
            "Job discovery execution completed",
            extra={
                "total_jobs_collected": len(all_collected_jobs),
                "total_execution_time_seconds": round(duration, 2)
            }
        )

        return all_collected_jobs

    def _filter_real_job_records(self, jobs: list[JobOpportunity]) -> list[JobOpportunity]:
        """
        Drop obvious non-job records: generic search result pages that are not
        individual job listings, and known mock/fallback records.

        We deliberately do NOT filter on query params like 'q=' or 'keywords='
        because many real individual job listing URLs from Naukri, Indeed, etc.
        legitimately include those params. We only drop clearly useless patterns.
        """
        filtered: list[JobOpportunity] = []
        skipped = 0

        # These URL patterns are definitively search result pages, not job listings
        blocklist_url_patterns = [
            "linkedin.com/jobs/search",
            "indeed.com/jobs?q=",
            "naukri.com/jobs?keyword=",
            "glassdoor.com/Job/jobs.htm",
        ]

        # These are mock company names from fallback_data.py — drop them
        mock_company_prefixes = ("techcorp", "startupxyz", "fintech ai", "medihealth", "agripredict", "logismart", "cognitive systems", "devtool")

        for job in jobs:
            url = (job.application_url or "").lower()
            company = (job.company or "").lower()

            # Must be a valid URL
            if not url.startswith(("http://", "https://")):
                skipped += 1
                continue

            # Drop known generic search result pages
            if any(pattern in url for pattern in blocklist_url_patterns):
                skipped += 1
                continue

            # Drop mock/fallback company names
            if any(company.startswith(prefix) for prefix in mock_company_prefixes):
                skipped += 1
                continue

            filtered.append(job)

        logger.info(
            "Real-job validation gate completed",
            extra={"input_jobs": len(jobs), "kept_jobs": len(filtered), "skipped_jobs": skipped},
        )
        return filtered

    def discover_new_companies(self) -> list[str]:
        """
        Search for new AI startup career pages and update the company discovery cache.

        Returns
        -------
        list[str]
            List of newly discovered company domain/career URLs.
        """
        logger.info("Dynamic company discovery triggered")

        # Load existing cache
        cache = self._load_company_cache()
        existing_urls = set(cache.get("career_urls", []))

        # Simulating search and discovery results
        newly_found = [
            "https://careers.sarvam.ai",
            "https://krutrim.ai/careers",
            "https://careers.hanooman.ai",
            "https://cohere.com/careers"
        ]

        added = []
        for url in newly_found:
            if url not in existing_urls:
                existing_urls.add(url)
                added.append(url)

        if added:
            cache["career_urls"] = sorted(list(existing_urls))
            self._save_company_cache(cache)
            logger.info("New AI startup career pages discovered", extra={"added_count": len(added), "urls": added})
        else:
            logger.info("No new AI startup career pages discovered in this run.")

        return added

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _run_tier_parallel(
        self,
        scrapers: list[Any],
        keywords: list[str],
        location: str,
        tier_label: str
    ) -> list[JobOpportunity]:
        """Run a set of scrapers in parallel using a thread pool."""
        logger.info(f"Starting {tier_label} scrapers execution in parallel")
        tier_start = time.time()
        collected: list[JobOpportunity] = []

        # We cap threads to avoid overwhelming resources. Honor config.scarper_max_workers
        try:
            max_workers = min(int(settings.scraper_max_workers), len(scrapers))
        except Exception:
            max_workers = min(8, len(scrapers))

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=tier_label.replace(" ", "")) as executor:
            futures = {}
            for scraper in scrapers:
                # Scrape each keyword
                for kw in keywords[:3]:  # limit to top 3 keywords per scraper invocation to avoid overwhelming
                    futures[executor.submit(self._scraper_job, scraper, kw, location)] = (scraper.source_name, kw)

            for future in as_completed(futures):
                source, kw = futures[future]
                try:
                    jobs = future.result()
                    collected.extend(jobs)
                    logger.info(
                        f"Source completed successfully",
                        extra={
                            "source": source,
                            "keyword": kw,
                            "jobs_collected": len(jobs)
                        }
                    )
                except Exception as exc:
                    logger.error(
                        f"Source failed during scraping execution",
                        extra={
                            "source": source,
                            "keyword": kw,
                            "error": str(exc)
                        }
                    )

        duration = time.time() - tier_start
        logger.info(
            f"Finished {tier_label} execution",
            extra={
                "tier": tier_label,
                "jobs_collected": len(collected),
                "duration_seconds": round(duration, 2)
            }
        )
        return collected

    def _scraper_job(self, scraper: Any, keyword: str, location: str) -> list[JobOpportunity]:
        """Wrapper executed in threads: optionally run browser inspection, then scrape."""
        try:
            try:
                scraper.maybe_inspect(keyword, location)
            except Exception:
                # Ensure inspection failure does not block scraping
                pass

            # Read from browser-rendered cache if use_browser is enabled
            html = None
            if settings.use_browser:
                try:
                    cache_file = scraper.get_cache_file_path(keyword, location)
                    if cache_file.exists():
                        html = cache_file.read_text(encoding="utf-8")
                        logger.info(f"Loaded browser-rendered HTML from cache for {scraper.source_name}")
                except Exception as exc:
                    logger.debug(f"Failed to read cached HTML for {scraper.source_name}: {exc}")

            return scraper.scrape(keyword, location, html=html)
        except Exception:
            # Re-raise to be handled by the caller which logs errors
            raise

    def _load_company_cache(self) -> dict[str, list[str]]:
        """Load discovered companies JSON cache from disk."""
        if self.company_cache_file.exists():
            try:
                return json.loads(self.company_cache_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(f"Failed to load company cache: {exc}")
        return {"career_urls": []}

    def _save_company_cache(self, cache_data: dict[str, list[str]]) -> None:
        """Save discovered companies JSON cache to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.company_cache_file.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error(f"Failed to write company cache file: {exc}")
