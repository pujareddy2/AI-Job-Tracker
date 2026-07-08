"""
filters/stages/technology_matching.py — Stage 6 Technology Matcher
==================================================================
Purpose
-------
Calculate match scores based on technology keywords inside description.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class TechnologyMatchingFilter(BaseFilter):
    """
    Stage 6: Tech stack match scoring.
    """

    filter_name = "TechnologyMatching"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        skill_groups = {
            "Python Ecosystem": ["python", "fastapi", "flask", "django"],
            "LLM Technologies": ["llm", "openai", "anthropic", "claude", "gemini", "llama", "mistral", "langchain", "langgraph"],
            "RAG & Vector": ["rag", "vector search", "embeddings", "pinecone", "chroma", "milvus", "faiss", "qdrant", "weaviate"],
            "AI General": ["ai", "machine learning", "generative ai", "nlp", "backend", "automation", "artificial intelligence", "deep learning"]
        }

        for job in jobs:
            desc = job.job.job_description.lower()
            title = job.job.job_title.lower()
            matched = set()
            missing = set()

            for group_name, keywords in skill_groups.items():
                # If any keyword in the group matches, the whole group is a "match" for similarity
                if any(k in desc or k in title for k in keywords):
                    matched.add(group_name)
                    # We can also add the specific keywords found
                    matched.update([k for k in keywords if k in desc or k in title])
                else:
                    missing.add(group_name)

            # Assign score based on how many groups were hit vs total groups
            total_groups = len(skill_groups)
            # Just count the top level groups that matched
            matched_groups = [g for g in skill_groups.keys() if g in matched]
            score = int((len(matched_groups) / total_groups) * 100) if total_groups else 0
            
            job.resume_match.candidate_match_score = score
            job.resume_match.resume_keywords_matched = list(matched)
            job.resume_match.resume_keywords_missing = list(missing)

            # NEVER reject based on 0 match score here (trust the ATS engine later)
            passed.append(job)

        return passed
