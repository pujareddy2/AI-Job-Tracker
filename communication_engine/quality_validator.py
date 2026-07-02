"""
communication_engine/quality_validator.py — Quality scoring and validation
==========================================================================
Purpose
-------
Rule-based scoring across 6 dimensions: readability, professionalism,
personalization, truthfulness confidence, grammar, and completeness.
Ensures zero unresolved placeholders and strict truthfulness.
"""

from __future__ import annotations

import re
from typing import Any

from communication_engine.config import QualityWeights
from communication_engine.models import QualityScoreCard


class QualityValidator:
    """Validates and scores generated outreach documents on quality and truthfulness."""

    def __init__(self, weights: QualityWeights) -> None:
        self.weights = weights

    def validate(
        self,
        document_type: str,
        body: str,
        profile: dict[str, Any],
        company_name: str,
        job_title: str,
    ) -> QualityScoreCard:
        """
        Evaluate and score a generated document.

        Parameters
        ----------
        document_type : str
        body : str
        profile : dict
        company_name, job_title : str

        Returns
        -------
        QualityScoreCard
        """
        # 1. Readability Score
        readability = self._score_readability(body, document_type)

        # 2. Professionalism Score
        professionalism = self._score_professionalism(body)

        # 3. Personalization Score
        personalization = self._score_personalization(body, profile, company_name, job_title)

        # 4. Truthfulness Confidence
        truthfulness = self._score_truthfulness(body, profile)

        # 5. Grammar & Spelling Score
        grammar = self._score_grammar(body)

        # 6. Completeness Score
        completeness = self._score_completeness(body)

        # Weighted Overall
        overall = (
            readability * self.weights.readability +
            professionalism * self.weights.professionalism +
            personalization * self.weights.personalization +
            truthfulness * self.weights.truthfulness +
            grammar * self.weights.grammar +
            completeness * self.weights.completeness
        )
        overall = round(min(overall, 100.0), 2)

        explanation = (
            f"Overall quality score: {overall:.1f}/100. Readability: {readability:.0f}, "
            f"Professionalism: {professionalism:.0f}, Personalization: {personalization:.0f}, "
            f"Truthfulness Confidence: {truthfulness:.0f}, Grammar: {grammar:.0f}, "
            f"Completeness: {completeness:.0f}."
        )

        return QualityScoreCard(
            readability_score=readability,
            professionalism_score=professionalism,
            personalization_score=personalization,
            truthfulness_confidence=truthfulness,
            grammar_score=grammar,
            completeness_score=completeness,
            overall_quality_score=overall,
            explanation=explanation,
        )

    # ── Individual Dimension Evaluators ──────────────────────────────────────

    def _score_readability(self, body: str, doc_type: str) -> float:
        """Cover letters have optimal size ~150-300 words. Email: 50-150 words."""
        words = len(body.split())
        if "cover letter" in doc_type.lower():
            if 150 <= words <= 350:
                return 100.0
            elif words < 150:
                return max(40.0, 100.0 - (150 - words) * 0.5)
            else:
                return max(40.0, 100.0 - (words - 350) * 0.2)
        else:
            # Email / LinkedIn
            if 30 <= words <= 200:
                return 100.0
            elif words < 30:
                return max(40.0, 100.0 - (30 - words) * 2.0)
            else:
                return max(30.0, 100.0 - (words - 200) * 0.5)

    def _score_professionalism(self, body: str) -> float:
        """Check greetings, closings, and absence of slang/emojis."""
        score = 100.0
        body_lower = body.lower()

        # Check for informal slang
        slang = ["wanna", "gonna", "lol", "lmao", "omg", "hey bro", "y'all"]
        for s in slang:
            if s in body_lower:
                score -= 20

        # Emojis check
        if any(char in body for char in ["😊", "👍", "🚀", "🔥", "🙌"]):
            score -= 10

        # Greeting check
        greetings = ["dear", "hello", "hi", "to the", "respectfully"]
        if not any(body_lower.startswith(g) for g in greetings):
            score -= 15

        return max(0.0, score)

    def _score_personalization(
        self, body: str, profile: dict[str, Any], company_name: str, job_title: str
    ) -> float:
        """Check that the document includes specific candidate and job names."""
        score = 0.0
        body_lower = body.lower()

        # Company Name
        if company_name.lower() in body_lower:
            score += 30
        # Job Title
        if job_title.lower() in body_lower:
            score += 30

        # Candidate Name
        c_name = profile.get("personal", {}).get("name", "").lower()
        if c_name and c_name in body_lower:
            score += 20

        # Tech/Institution check
        inst = profile.get("education", {}).get("institution", "").lower()
        if inst and any(word in body_lower for word in inst.split()[:2]):
            score += 20

        return score

    def _score_truthfulness(self, body: str, profile: dict[str, Any]) -> float:
        """
        Verify that all mentioned tech skills are present in candidate profile
        to prevent exaggeration or hallucination.
        """
        body_lower = body.lower()
        
        # Collect candidate's real skills
        skills_flat = set()
        for cat_skills in profile.get("skills", {}).values():
            if isinstance(cat_skills, list):
                skills_flat.update(s.lower() for s in cat_skills)
        for proj in profile.get("projects", []):
            skills_flat.update(t.lower() for t in proj.get("technologies", []))
        for intern in profile.get("experience", {}).get("internships", []):
            skills_flat.update(t.lower() for t in intern.get("technologies", []))
        for ext_list in profile.get("expanded_keywords", {}).values():
            if isinstance(ext_list, list):
                skills_flat.update(s.lower() for s in ext_list)

        # Check common high-profile technologies. If mentioned, they MUST be in skills_flat.
        tech_list = ["pytorch", "tensorflow", "fastapi", "django", "flask", "react", "next.js",
                     "kubernetes", "docker", "aws", "gcp", "azure", "sql", "postgresql",
                     "langchain", "llama", "scikit-learn", "numpy", "pandas", "java", "python"]

        unauthorized = []
        for tech in tech_list:
            if tech in body_lower and tech not in skills_flat:
                # Synonym mapping check (e.g. react.js vs react)
                if tech == "react" and ("react.js" in skills_flat or "reactjs" in skills_flat):
                    continue
                if tech == "fastapi" and ("fast api" in skills_flat or "fast-api" in skills_flat):
                    continue
                unauthorized.append(tech)

        if unauthorized:
            # Deduct points per unauthorized technology
            deduction = len(unauthorized) * 30
            return max(10.0, 100.0 - deduction)

        return 100.0

    def _score_grammar(self, body: str) -> float:
        """Check basic grammar proxies like double spaces, lowercase start sentences, etc."""
        score = 100.0
        
        # Check double spaces
        if "  " in body:
            score -= 10
            
        # Check sentences starting with lowercase
        sentences = re.split(r"[.!?]\s+", body)
        for s in sentences:
            if s and s[0].islower() and not s.startswith("http"):
                score -= 15
                break

        return max(0.0, score)

    def _score_completeness(self, body: str) -> float:
        """Ensure NO unresolved placeholders exist (like [Company Name], {job_title})."""
        placeholders = [
            r"\[.*?\]",  # e.g. [Company Name]
            r"\{.*?\}",  # e.g. {company_name}
            r"Insert\s+\w+",
            r"<.*?>"
        ]
        for pattern in placeholders:
            if re.search(pattern, body):
                return 0.0  # Hard penalty for unresolved templates

        return 100.0
