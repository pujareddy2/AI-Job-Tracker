import re
from typing import List, Set
from utils.logger import get_logger

logger = get_logger(__name__)

class SearchIntelligence:
    """Dynamically generates search queries and semantic variations from base roles."""

    # Pre-computed mappings for common AI/Software roles
    SEMANTIC_MAP = {
        "applied ai engineer": [
            "AI Engineer", "AI Software Engineer", "AI Developer", "ML Engineer",
            "Machine Learning Engineer", "GenAI Engineer", "Generative AI Engineer",
            "LLM Engineer", "Python AI Developer", "AI Backend Engineer",
            "AI Automation Engineer", "AI Integration Engineer", 
            "Conversational AI Engineer", "Agentic AI Engineer",
            "Backend ML Engineer"
        ],
        "machine learning engineer": [
            "ML Engineer", "Machine Learning Engineer", "AI Engineer", "Applied Scientist",
            "Data Scientist", "Deep Learning Engineer"
        ],
        "backend developer": [
            "Backend Engineer", "Backend Developer", "Software Engineer Backend",
            "Python Developer", "API Developer", "Server Side Engineer"
        ],
        "full stack developer": [
            "Fullstack Engineer", "Full Stack Developer", "Software Engineer Full Stack",
            "Web Developer"
        ]
    }

    # Levels that can be appended to queries
    LEVELS = [
        "Graduate",
        "Associate",
        "Entry Level",
        "Campus Hiring",
        "Early Career",
        "Junior",
        "New Grad"
    ]

    @staticmethod
    def expand_query(base_role: str, target_levels: bool = True) -> List[str]:
        """
        Expands a single role into hundreds of semantic variations based on mapped synonyms
        and experience levels.
        """
        role_lower = base_role.lower().strip()
        variations: Set[str] = {base_role}

        # Find synonyms
        for key, synonyms in SearchIntelligence.SEMANTIC_MAP.items():
            if key in role_lower or role_lower in key:
                variations.update(synonyms)

        expanded_queries = set(variations)
        
        # Optionally multiply with level permutations (for entry-level focus)
        if target_levels:
            for v in variations:
                for level in SearchIntelligence.LEVELS:
                    expanded_queries.add(f"{level} {v}")
                    expanded_queries.add(f"{v} {level}")

        # Deduplicate and sort
        final_list = list(expanded_queries)
        logger.debug(f"SearchIntelligence expanded '{base_role}' into {len(final_list)} variations.")
        return final_list
