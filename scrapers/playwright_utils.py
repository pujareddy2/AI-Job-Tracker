import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_html_with_playwright(url: str, wait_for_selector: Optional[str] = None) -> str:
    """
    Fetches the HTML content of a URL using a headless Playwright Chromium browser.
    This effectively bypasses basic bot protections (like Cloudflare) and allows
    JavaScript-rendered single-page applications to load before extracting the HTML.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright is not installed. Please run: pip install playwright && playwright install chromium")
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            # Route interception to block images and fonts for speed and lower detection
            page.route("**/*", lambda route: route.continue_() if route.request.resource_type not in ["image", "font", "media"] else route.abort())
            
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=10000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for selector {wait_for_selector}: {e}")
            
            # Fixed timeout to allow React/Angular to hydrate the DOM
            page.wait_for_timeout(3000)
            
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright execution failed for {url}: {e}")
        return ""
