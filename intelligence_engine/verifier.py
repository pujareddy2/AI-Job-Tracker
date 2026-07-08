import re
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

class Verifier:
    """Verifies official job links ensuring they are live, direct applications, and not expired."""

    @staticmethod
    def verify_official_link(url: str, check_live: bool = True) -> bool:
        """
        Validate if a URL is a direct application link.
        """
        if not url:
            return False
            
        url_lower = url.lower()

        # 1. Reject search result URLs, homepages, and login gates
        reject_patterns = [
            r"/jobs/search", r"/search\?", r"google.com/search", r"bing.com",
            r"indeed.com/jobs\?", r"naukri.com/.*-jobs", r"linkedin.com/jobs/search",
            r"/careers$", r"/careers/$", r"careers\.[a-z0-9\-]+\.[a-z]+$",
            r"login", r"/signin", r"/signup", r"/auth", r"/register", r"accounts\.google\.com",
            r"/password/reset", r"/forgot-password"
        ]

        for pattern in reject_patterns:
            if re.search(pattern, url_lower):
                logger.debug(f"URL Verification Failed (Pattern Match): {url}")
                return False

        # 2. Must be HTTPS
        if not url.startswith("https://"):
            logger.debug(f"URL Verification Failed (Not HTTPS): {url}")
            return False

        # 3. Live check for HTTP 200 and expired terminology
        if check_live:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
                
                if res.status_code != 200:
                    logger.debug(f"URL Verification Failed (HTTP {res.status_code}): {url}")
                    return False
                
                # Verify we didn't get redirected to a login page or search
                final_url = res.url.lower()
                for pattern in reject_patterns:
                    if re.search(pattern, final_url):
                        logger.debug(f"URL Verification Failed (Redirected to bad pattern): {res.url}")
                        return False
                
                # Check for expiration terms in HTML body
                body_lower = res.text.lower()
                expire_keywords = [
                    "no longer accepting applications", "job is closed", "job posting has expired",
                    "position has been filled", "no longer active", "this job is no longer available"
                ]
                if any(kw in body_lower for kw in expire_keywords):
                    logger.debug(f"URL Verification Failed (Job Expired Text Found): {url}")
                    return False

            except requests.RequestException as e:
                logger.debug(f"URL Verification Failed (Network Error - {e}): {url}")
                return False

        logger.debug(f"URL Verification Passed: {url}")
        return True
