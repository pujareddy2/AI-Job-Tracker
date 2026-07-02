"""
resume_matcher/semantic_intelligence.py — Semantic Synonym and Relation Mapper
=============================================================================
Purpose
-------
Resolve relationships between technologies, frameworks, and tools.
"""

from __future__ import annotations


class SemanticIntelligence:
    """
    Handles semantic expansions and checks without requiring exact string equality.
    """

    # Semantic relationships mapping a tech keyword to its related synonyms and concepts
    RELATIONSHIPS = {
        "fastapi": ["rest apis", "backend", "python backend", "microservices", "web development", "apis"],
        "langchain": ["llms", "ai agents", "rag", "knowledge retrieval", "prompt engineering", "openai apis", "llm applications"],
        "langgraph": ["ai agents", "agentic", "workflows", "state machines", "langchain"],
        "llamaindex": ["rag", "vector databases", "information retrieval", "llm applications", "index"],
        "postgresql": ["sql", "databases", "sqlalchemy", "orm", "relational database", "database design"],
        "docker": ["containerization", "deployment", "microservices", "devops", "kubernetes"],
        "git": ["version control", "github", "gitlab", "collaboration"],
        "openai": ["llms", "gpt", "generative ai", "chatgpt", "claude", "gemini"],
        "gemini": ["llms", "generative ai", "apis", "google ai"],
        "chromadb": ["vector database", "rag", "embeddings", "pinecone", "milvus", "qdrant", "weaviate"],
        "pinecone": ["vector database", "embeddings", "rag", "chromadb"],
        "transformers": ["hugging face", "deep learning", "nlp", "llms", "bert", "gpt"],
        "tensorflow": ["deep learning", "machine learning", "keras", "neural networks", "pytorch"],
        "pytorch": ["deep learning", "machine learning", "neural networks", "tensorflow"]
    }

    @classmethod
    def get_related_terms(cls, term: str) -> list[str]:
        """Get related technical terms/concepts for a given skill."""
        term_clean = term.strip().lower()
        
        # Check direct map
        related = cls.RELATIONSHIPS.get(term_clean, [])
        if related:
            return [term_clean] + related
            
        # Reverse check (if term matches a concept in relationships)
        terms = [term_clean]
        for key, values in cls.RELATIONSHIPS.items():
            if term_clean in values:
                terms.append(key)
        return terms

    @classmethod
    def check_match(cls, skill: str, target_text: str) -> bool:
        """
        Check if a skill matches a text semantically.

        Parameters
        ----------
        skill : str
            Candidate skill technology.
        target_text : str
            Job description or requirement text.

        Returns
        -------
        bool
            True if matched.
        """
        target_clean = target_text.lower()
        related_terms = cls.get_related_terms(skill)
        
        # Match if any related term is in target
        return any(term in target_clean for term in related_terms)
