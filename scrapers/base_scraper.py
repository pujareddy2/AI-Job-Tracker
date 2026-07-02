"""
scrapers/base_scraper.py — Abstract Base Class for All Scrapers
===============================================================
Purpose
-------
Define the interface (contract) that every job-board scraper must implement.
Using an abstract base class ensures:
    1. All scrapers expose identical methods, so the scheduler can call
       them interchangeably without knowing which board they target.
    2. Missing method implementations are caught at class-definition time,
       not at runtime.
    3. Shared logic (HTTP session setup, timeout config, retry wiring)
       lives here once and is inherited by all concrete scrapers.

Responsibilities
----------------
- Define abstract methods: `scrape()`, `validate_config()`.
- Provide a reusable `_get_session()` method that returns a `requests.Session`
  pre-configured with headers, timeouts, and retry behaviour.
- Hold common attributes: `source_name`, `base_url`, `logger`.

Concrete scrapers (Phase 2+)
-----------------------------
    scrapers/linkedin.py   → LinkedInScraper(BaseScraper)
    scrapers/indeed.py     → IndeedScraper(BaseScraper)
    scrapers/glassdoor.py  → GlassdoorScraper(BaseScraper)

Usage (future)
--------------
    from scrapers.linkedin import LinkedInScraper
    scraper = LinkedInScraper()
    jobs = scraper.scrape(keyword="ML Engineer", location="Remote")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests
import time
import urllib.parse

from config import settings

from scrapers.models import JobOpportunity
from utils.logger import get_logger


class BaseScraper(ABC):
    """
    Abstract base class for all job-board scrapers.

    Subclasses MUST implement:
        - scrape()
        - validate_config()

    Attributes
    ----------
    source_name : str
        Human-readable name of the job board (e.g., "LinkedIn").
    base_url : str
        Root URL of the job board.
    timeout : int
        HTTP request timeout in seconds.  Default: 30.
    reliability_score : int
        The default trust score assigned to listings from this source (0-100).
    """

    source_name: str = "BaseSource"
    base_url: str = ""
    timeout: int = 30
    reliability_score: int = 50
    returns_live_data: bool = False

    def __init__(self) -> None:
        self.logger = get_logger(f"scrapers.{self.source_name.lower().replace(' ', '_')}")
        self._session: requests.Session | None = None

    # -------------------------------------------------------------------------
    # Abstract interface — must be implemented by every subclass
    # -------------------------------------------------------------------------

    @abstractmethod
    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        """
        Scrape job listings from the board.


        Parameters
        ----------
        keyword : str
            Job title or skill to search for (e.g., "Python Developer").
        location : str
            Geographic location or "Remote".
        **kwargs : Any
            Board-specific parameters (e.g., experience_level, date_posted).

        Returns
        -------
        list[JobOpportunity]
            List of normalized JobOpportunity records.
        """

    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate that all required configuration values for this scraper
        are present (e.g., API keys, session cookies).

        Raises
        ------
        ConfigurationError
            If a required configuration value is missing or invalid.
        """

    # -------------------------------------------------------------------------
    # Shared concrete methods
    # -------------------------------------------------------------------------

    def _get_session(self) -> requests.Session:
        """
        Return (or create) a reusable HTTP session with sensible defaults.

        The session is created lazily on first use and reused for all
        subsequent requests within a single scraper run — this is more
        efficient than opening a new TCP connection per request.
        """
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
        return self._session

    def close(self) -> None:
        """
        Close the underlying HTTP session and release connections.

        Call this when the scraper is done (or use it as a context manager
        in Phase 2 by implementing __enter__ / __exit__).
        """
        if self._session is not None:
            self._session.close()
            self._session = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.source_name!r}>"

    def get_search_url(self, keyword: str, location: str) -> str:
        """
        Construct the search URL for this scraper. Overridden by concrete classes.
        """
        if not self.base_url:
            return ""
        query = urllib.parse.quote(keyword or "")
        loc_q = urllib.parse.quote(location or "")
        return f"{self.base_url}?keywords={query}&location={loc_q}"

    def get_cache_file_path(self, keyword: str, location: str) -> Path:
        """Get the absolute path to the cached HTML file for this search query."""
        safe_kw = "".join(c for c in (keyword or "") if c.isalnum() or c in ("-", "_"))[:40]
        safe_loc = "".join(c for c in (location or "") if c.isalnum() or c in ("-", "_"))[:40]
        return settings.cache_dir / f"{self.source_name.lower().replace(' ', '_')}_{safe_kw}_{safe_loc}.html"

    def maybe_inspect(self, keyword: str, location: str) -> None:
        """
        Optionally launch a browser (Selenium or Playwright) to inspect a
        search/result page and save the HTML into `settings.cache_dir` for
        later inspection and parsing.

        This is a no-op unless `settings.use_browser` is True. When
        `settings.browser_detach` is true and `browser_headless` is false the
        browser will be left open so you can watch the automation live.
        """
        if not settings.use_browser:
            return

        url = self.get_search_url(keyword, location)
        if not url:
            return

        try:
            self.logger.info("Inspecting page via browser", extra={"source": self.source_name, "url": url, "engine": settings.browser_engine, "headless": settings.browser_headless})

            if settings.browser_engine == "selenium":
                try:
                    from utils.browser import create_chrome_driver
                except Exception as exc:
                    self.logger.warning(f"Selenium helper not available: {exc}")
                    return

                driver = create_chrome_driver(headless=settings.browser_headless)
                try:
                    driver.get(url)
                    # Allow JS to load
                    time.sleep(5)
                    html = driver.page_source
                finally:
                    # If configured to detach and the browser is visible, leave it open for inspection
                    if not (settings.browser_detach and not settings.browser_headless):
                        try:
                            driver.quit()
                        except Exception:
                            pass

            elif settings.browser_engine == "playwright":
                try:
                    from playwright.sync_api import sync_playwright
                except Exception as exc:
                    self.logger.warning(f"Playwright not installed or unavailable: {exc}")
                    return

                html = None
                try:
                    # If detaching (live-visible) we must start Playwright without closing the driver context.
                    if settings.browser_detach and not settings.browser_headless:
                        p = sync_playwright().start()
                        browser = p.chromium.launch(headless=False, devtools=True, slow_mo=int(settings.browser_slow_mo) or None)
                        page = browser.new_page(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                            viewport={"width": 1280, "height": 1024}
                        )
                        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        page.goto(url, timeout=45000)
                        page.wait_for_timeout(5000)
                        html = page.content()
                        # Do not close the browser or stop Playwright so the window remains open for inspection
                        self.logger.info("Playwright launched and left open for inspection (browser_detach=True)")
                        return
                    else:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=bool(settings.browser_headless), slow_mo=int(settings.browser_slow_mo) or None)
                            page = browser.new_page(
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                                viewport={"width": 1280, "height": 1024}
                            )
                            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                            page.goto(url, timeout=45000)
                            page.wait_for_timeout(5000)
                            html = page.content()
                            browser.close()
                except Exception as exc:
                    self.logger.warning(f"Playwright inspection failed: {exc}")
                    return

            else:
                # Unknown engine
                self.logger.warning(f"Unknown browser engine configured: {settings.browser_engine}")
                return

            # Persist HTML for debugging if we got content
            if html:
                try:
                    out_file = self.get_cache_file_path(keyword, location)
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                    out_file.write_text(html, encoding="utf-8")
                    self.logger.info("Saved inspection HTML", extra={"path": str(out_file)})
                except Exception as exc:
                    self.logger.warning(f"Failed to write inspection HTML: {exc}")

        except Exception as exc:
            # Do not raise — inspection must not break scraping
            self.logger.warning(f"Browser inspection failed for {self.source_name}: {exc}")

