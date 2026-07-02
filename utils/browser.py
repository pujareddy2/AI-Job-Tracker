"""
utils/browser.py
-----------------
Small helper to create a headless Chrome webdriver for optional browser-based
automation (Selenium). This file is intentionally lightweight and optional —
the code only runs when a scraper or helper opts into launching a real
browser. The project currently defaults to HTTP requests for scraping.

Usage:
    from utils.browser import create_chrome_driver
    driver = create_chrome_driver(headless=True)
    try:
        driver.get("https://example.com")
        ...
    finally:
        driver.quit()
"""

from __future__ import annotations

import os
from typing import Tuple

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
except Exception:  # pragma: no cover - optional dependency
    webdriver = None  # type: ignore


def create_chrome_driver(headless: bool = True, window_size: Tuple[int, int] = (1280, 1024)):
    """
    Create and return a Chrome webdriver configured for headless operation.

    - Tries to use system-installed chromedriver first.
    - If `webdriver-manager` is installed it will be used to provide a driver binary.

    Note: Add `selenium` (and optionally `webdriver-manager`) to `requirements.txt`
    if you intend to run browser-based scrapers.
    """

    if webdriver is None:
        raise RuntimeError("Selenium is not installed. Install with: pip install selenium")

    options = Options()
    # Use new headless mode when available
    if headless:
        try:
            options.add_argument("--headless=new")
        except Exception:
            options.add_argument("--headless")

    options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    # Stealth options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    # Prefer webdriver-manager if available to avoid manual chromedriver installation
    service = None
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except Exception:
        # Fall back to system chromedriver (Service(None)) and let webdriver find it
        try:
            service = Service()
        except Exception:
            service = None

    if service is not None:
        return webdriver.Chrome(service=service, options=options)
    return webdriver.Chrome(options=options)
