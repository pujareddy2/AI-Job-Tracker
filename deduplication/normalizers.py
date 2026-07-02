"""
deduplication/normalizers.py — Entity Normalizers
=================================================
Purpose
-------
Normalize text values (companies, roles, locations) using alias mappings.
"""

from __future__ import annotations

import re
from typing import Any


class EntityNormalizer:
    """
    Cleans company names, job titles, and locations to standardize variations.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.company_aliases = config.get("company_aliases", {})
        self.role_aliases = config.get("role_aliases", {})
        self.location_aliases = config.get("location_aliases", {})

    def normalize_company(self, company: str) -> str:
        """
        Normalize company names by resolving aliases and stripping common suffixes.
        """
        if not company:
            return "Unknown"

        comp_lower = company.strip().lower()
        
        # Check explicit aliases
        if comp_lower in self.company_aliases:
            return self.company_aliases[comp_lower]

        # Strip common legal suffixes
        cleaned = re.sub(
            r"\b(llc|inc|corp|corporation|ltd|pvt|private|limited|co|india|global)\b",
            "",
            comp_lower,
            flags=re.IGNORECASE
        )
        
        # Clean whitespaces
        cleaned_str = " ".join(cleaned.split()).title()
        return cleaned_str if cleaned_str else company.strip()

    def normalize_role(self, title: str) -> str:
        """
        Normalize job titles to resolve synonym variations.
        """
        if not title:
            return "Unknown"

        title_lower = title.strip().lower()
        
        # Exact match alias
        if title_lower in self.role_aliases:
            return self.role_aliases[title_lower]

        # Pattern matches
        if any(term in title_lower for term in ["applied ai", "generative ai", "llm", "rag", "ai engineer"]):
            return "AI Engineer"
        if any(term in title_lower for term in ["python ai", "ai backend", "backend ai"]):
            return "AI Backend Engineer"
            
        # Title case default clean
        return title.strip().title()

    def normalize_location(self, location: str) -> str:
        """
        Normalize locations to a consistent format (e.g. Remote, City names).
        """
        if not location:
            return "Unknown"

        loc_lower = location.strip().lower()
        
        if loc_lower in self.location_aliases:
            return self.location_aliases[loc_lower]

        if "remote" in loc_lower or "wfh" in loc_lower or "work from home" in loc_lower:
            return "Remote"
            
        if "hyderabad" in loc_lower:
            return "Hyderabad"
        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            return "Bangalore"
        if "pune" in loc_lower:
            return "Pune"
            
        # Clean other variations
        parts = [p.strip().title() for p in location.split(",")]
        return parts[0]
