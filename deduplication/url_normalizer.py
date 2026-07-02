"""
deduplication/url_normalizer.py — Canonical URL Normalizer
=========================================================
Purpose
-------
Normalize application and tracking URLs, stripping query tracking,
referrals, and UTM parameters.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class URLNormalizer:
    """
    Strips UTM params and standardizes job referral and portal redirection URLs.
    """

    # Tracking URL parameter keys to strip
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "refid", "referrer", "origin", "trackingid", "trk", "affiliate", "spm",
        "context", "clickid", "gclid", "fbclid"
    }

    @classmethod
    def clean_url(cls, url: str) -> str:
        """
        Strip query trackers, lower hostnames, and resolve canonical link structure.

        Parameters
        ----------
        url : str
            Raw application or listing link.

        Returns
        -------
        str
            Standardized canonical link.
        """
        if not url:
            return ""

        url_str = url.strip()
        
        # 1. Basic format fix
        if not url_str.startswith(("http://", "https://")):
            url_str = "https://" + url_str

        try:
            parsed = urlparse(url_str)
            
            # Lowercase scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path
            
            # Standardize LinkedIn paths
            # e.g., linkedin.com/jobs/view/123456 or linkedin.com/jobs/view/detail/123456 -> same canonical format
            if "linkedin.com" in netloc and "/jobs/view" in path:
                # Extract job ID
                job_id_match = re.search(r"/view/(?:detail/)?(\d+)", path)
                if job_id_match:
                    path = f"/jobs/view/{job_id_match.group(1)}"

            # 2. Filter tracking params from query
            query_items = parse_qsl(parsed.query)
            cleaned_query_items = [
                (k, v) for k, v in query_items
                if k.lower() not in cls.TRACKING_PARAMS
            ]
            
            # Standardize order of query parameters to avoid duplicate permutations
            cleaned_query_items.sort()
            
            query = urlencode(cleaned_query_items) if cleaned_query_items else ""
            
            # Reconstruct URL (without fragment params)
            canonical = urlunparse((
                scheme,
                netloc,
                path,
                parsed.params,
                query,
                ""  # clear fragments
            ))
            
            return canonical
        except Exception:
            return url_str
