"""
communication_engine/templates.py — Template Registry and Automatic Selection
=============================================================================
Purpose
-------
Provides structured communication templates for Cover Letters, Emails, LinkedIn,
and Offer/Withdrawal drafts across 4 tones and 13 domains.

Design Decisions
----------------
- Python string formatting templates with clear placeholders.
- Automatic, rule-based template selector scanning JD description and company profile.
"""

from __future__ import annotations

import re
from typing import Any

# ===========================================================================
# 1. Base Templates
# ===========================================================================

# ── Cover Letter Templates ────────────────────────────────────────────────
COVER_LETTER_TEMPLATES = {
    "Startup": (
        "Dear hiring team at {company_name},\n\n"
        "I am writing to express my enthusiasm for the {job_title} position. As a software engineering graduate "
        "passionate about building fast-paced, scale-up systems, {company_name}'s mission aligns perfectly with "
        "my goal of building scalable applications that drive user engagement.\n\n"
        "During my studies at {institution}, I maintained a CGPA of {cgpa} and focused heavily on practical software engineering. "
        "I developed {projects_paragraph}, utilizing technologies like {skills_paragraph}. "
        "Through this experience, I learned how to move quickly, iterate based on requirements, and maintain clean code—qualities "
        "that are vital to {company_name}'s high-growth environment. {internships_paragraph}\n\n"
        "I am eager to bring my background in {skills_paragraph} to your team and contribute to {company_name}'s growth. "
        "My career objective is to become a core contributor in engineering-first startups. Thank you for your time and "
        "consideration.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Enterprise": (
        "Dear Hiring Manager,\n\n"
        "Please accept this application for the {job_title} role at {company_name}. With a solid academic foundation in "
        "engineering from {institution} and hands-on experience in software development, I am eager to contribute to "
        "{company_name}'s enterprise systems.\n\n"
        "My educational background includes a strong performance at {institution} (CGPA: {cgpa}), specializing in {branch}. "
        "To apply my training, I built {projects_paragraph}, applying technical concepts to solve real-world problems. "
        "I am proficient in {skills_paragraph}, and I have learned to write resilient, well-documented code that fits "
        "enterprise standards. {internships_paragraph}\n\n"
        "I admire {company_name}'s leadership in its sector, and I am excited about the opportunity to join a structured "
        "engineering organization where I can contribute to high-availability systems. I look forward to discussing how "
        "my skills align with your engineering standards.\n\n"
        "Respectfully yours,\n\n{candidate_name}"
    ),
    "FinTech": (
        "Dear {company_name} Hiring Team,\n\n"
        "I am writing to apply for the open {job_title} position. I am highly interested in how {company_name} is leveraging technology "
        "to optimize financial operations, and I would love to bring my technical skills in {skills_paragraph} to your organization.\n\n"
        "At {institution}, where I completed my studies in {branch} with a CGPA of {cgpa}, I built projects that required rigorous "
        "accuracy and data handling. For instance, I created {projects_paragraph}. This project helped me refine my skills in "
        "building secure, high-performance backends and database structures. {internships_paragraph}\n\n"
        "Fintech requires a strong commitment to reliability, performance, and security. I am eager to apply my skills in "
        "{skills_paragraph} to build robust, secure code at {company_name}. Thank you for your time and consideration.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Healthcare AI": (
        "Dear Hiring Committee,\n\n"
        "I am writing to express my strong interest in the {job_title} role at {company_name}. I am deeply interested in how "
        "healthcare AI systems improve patient outcomes, and I would be thrilled to contribute my background in {skills_paragraph} "
        "to {company_name}'s healthcare platform.\n\n"
        "Graduating with a CGPA of {cgpa} in {branch} from {institution}, I have focused my development work on high-impact AI "
        "and data processing. I built {projects_paragraph}, which demonstrated my ability to process complex data structures and "
        "integrate model components. {internships_paragraph}\n\n"
        "I look forward to the possibility of joining {company_name} and applying my engineering skills to build tools that "
        "support healthcare providers and patient care. Thank you for evaluating my application.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Generative AI": (
        "Dear hiring team,\n\n"
        "I am writing to express my strong interest in the {job_title} position at {company_name}. As an engineer specializing in "
        "Generative AI, LLMs, and RAG systems, I am excited about the prospect of contributing to {company_name}'s AI initiatives.\n\n"
        "My studies at {institution} (CGPA: {cgpa}) provided me with a strong background in computer science, which I applied to "
        "building state-of-the-art AI systems. For example, I built {projects_paragraph}, leveraging tools like {skills_paragraph}. "
        "This project deepened my knowledge of vector indexing, semantic search, and prompt engineering. {internships_paragraph}\n\n"
        "I am keen to help {company_name} deploy reliable, context-aware AI applications. My goal is to build generative systems "
        "that provide real business value. Thank you for your time.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Applied AI": (
        "Dear Hiring Manager,\n\n"
        "I am excited to apply for the {job_title} role at {company_name}. With my academic background from {institution} and "
        "practical engineering projects, I am eager to help {company_name} integrate artificial intelligence models into "
        "production workflows.\n\n"
        "During my undergraduate degree in {branch} (CGPA: {cgpa}), I focused on bridging the gap between machine learning models "
        "and production backends. I built {projects_paragraph}, utilizing a technology stack that includes {skills_paragraph}. "
        "This work taught me how to clean data, optimize performance, and serve model components reliably. {internships_paragraph}\n\n"
        "I am motivated by {company_name}'s focus on applied AI and would love to contribute to deploying production models. "
        "Thank you for your consideration.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "ML": (
        "Dear {company_name} ML Recruiting Team,\n\n"
        "I am writing to apply for the {job_title} position. I am highly interested in the machine learning work being done at "
        "{company_name}, and I believe my background in model training, evaluation, and pipeline development aligns well with your team.\n\n"
        "I completed my studies at {institution} with a CGPA of {cgpa}. I built {projects_paragraph}, utilizing {skills_paragraph}. "
        "This project allowed me to apply statistical analysis, design data cleaning pipelines, and evaluate model performance. "
        "{internships_paragraph}\n\n"
        "I am eager to contribute to {company_name}'s ML engineering team by building reliable training pipelines and optimizing "
        "inference performance. Thank you for your time.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "NLP": (
        "Dear Hiring Manager,\n\n"
        "I am writing to apply for the {job_title} role at {company_name}. With a background in natural language processing and "
        "information retrieval, I would love to join your team and contribute to {company_name}'s text analysis and language model pipelines.\n\n"
        "At {institution} (CGPA: {cgpa}), I specialized in language technology. I designed and built {projects_paragraph}, "
        "using tools like {skills_paragraph}. This project focused on text parsing, vector embeddings, and semantic matching. "
        "{internships_paragraph}\n\n"
        "I am excited about {company_name}'s language technology systems and would love to bring my technical skills to your team. "
        "Thank you for considering my application.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Backend": (
        "Dear Hiring Manager,\n\n"
        "I am writing to apply for the {job_title} position at {company_name}. With a strong foundation in backend software engineering "
        "and system design, I am eager to help {company_name} build high-performance APIs and data layers.\n\n"
        "During my degree in {branch} at {institution} (CGPA: {cgpa}), I focused on backend systems and database design. "
        "I built {projects_paragraph}, utilizing a tech stack of {skills_paragraph}. "
        "This project refined my skills in API design, database normalization, and structured software development. {internships_paragraph}\n\n"
        "I look forward to contributing to {company_name}'s engineering team and building robust, maintainable backends. "
        "Thank you for evaluating my application.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Remote": (
        "Dear hiring team at {company_name},\n\n"
        "I am writing to apply for the remote {job_title} position. As a software engineer accustomed to collaborative development, "
        "I am excited about the opportunity to join {company_name}'s distributed team.\n\n"
        "I graduated from {institution} with a CGPA of {cgpa} in {branch}. Operating in a self-directed environment, I built "
        "{projects_paragraph}, using version control and asynchronous collaboration tools. I am proficient in {skills_paragraph}, "
        "and I have learned to write self-documenting code and thorough tests. {internships_paragraph}\n\n"
        "I am highly self-motivated and eager to contribute to {company_name}'s engineering team remotely. Thank you for your time.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Internship": (
        "Dear {company_name} University Relations Team,\n\n"
        "I am writing to apply for the {job_title} position. As a student at {institution} seeking to apply my academic training, "
        "I would love the opportunity to join your engineering team as an intern.\n\n"
        "I am pursuing my degree in {branch} (current CGPA: {cgpa}) at {institution}. Outside of coursework, I have completed "
        "projects like {projects_paragraph}, utilizing {skills_paragraph}. These projects have helped me apply theoretical "
        "knowledge to practical software engineering. {internships_paragraph}\n\n"
        "I am eager to learn from your engineers and contribute to {company_name}'s projects during the internship. Thank you for "
        "your time and consideration.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Graduate Program": (
        "Dear University Recruiting Team,\n\n"
        "I am writing to apply for the {job_title} at {company_name}. Having recently completed my studies at {institution}, "
        "I am eager to join {company_name}'s graduate development program to build my engineering skills.\n\n"
        "I completed my degree in {branch} with a CGPA of {cgpa}. During my studies, I built {projects_paragraph}, utilizing "
        "{skills_paragraph}. This experience developed my technical foundations and collaborative skills. {internships_paragraph}\n\n"
        "I am excited to start my career with {company_name}'s structured training program and contribute to your team. "
        "Thank you for reviewing my application.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Entry-Level": (
        "Dear Hiring Manager,\n\n"
        "Please accept this application for the entry-level {job_title} position at {company_name}. As an engineering graduate "
        "from {institution}, I am excited to join {company_name} as an associate software engineer.\n\n"
        "At {institution}, I maintained a CGPA of {cgpa} and built projects to build my practical coding skills. For example, "
        "I created {projects_paragraph}, using {skills_paragraph}. This taught me the fundamentals of version control, code "
        "reviews, and automated testing. {internships_paragraph}\n\n"
        "I am highly motivated to learn your development processes and contribute to {company_name}'s products. Thank you for your time.\n\n"
        "Respectfully yours,\n{candidate_name}"
    ),
}

# ── Tone Modifier Helper ──────────────────────────────────────────────────
def modify_tone(text: str, tone: str) -> str:
    """Adjust the generated template text according to the selected tone version."""
    if tone == "Concise":
        # Make the paragraphs much shorter, remove introductory/concluding filler
        text = text.replace("I am writing to express my enthusiasm for", "I am applying for")
        text = text.replace("I am writing to apply for the open", "I am applying for the")
        text = text.replace("Please accept this application for the", "Please accept my application for")
        text = text.replace("Thank you for your time and consideration.", "Thank you.")
        text = text.replace("Thank you for evaluating my application.", "Thank you.")
        # Regex to cut out some fluff sentences
        text = re.sub(r"I am highly self-motivated and eager to.*", "", text)
        text = re.sub(r"I look forward to the possibility of.*", "", text)
    elif tone == "Formal":
        # Elevate greetings and endings, use more formal vocabulary
        text = text.replace("Dear hiring team", "Dear Sir or Madam")
        text = text.replace("Dear Hiring Manager", "To the Hiring Manager")
        text = text.replace("Sincerely,", "Sincerely yours,")
        text = text.replace("Best regards,", "Yours faithfully,")
    elif tone == "Friendly":
        # Use warmer tone and enthusiastic phrasing
        text = text.replace("Dear hiring team", "Hi Team")
        text = text.replace("Dear Hiring Manager", "Hi there")
        text = text.replace("Sincerely,", "Warmly,")
        text = text.replace("Respectfully yours,", "Best,")
        text = text.replace("Best regards,", "Warm regards,")
    return text


# ===========================================================================
# 2. Template Selector
# ===========================================================================

class TemplateSelector:
    """Matches a job opportunity to the best available communication template."""

    @staticmethod
    def select_template(job: dict[str, Any]) -> str:
        """
        Scan job description and company metadata to determine the best template.

        Selection hierarchy:
        1. Internship (if job_title or description mentions internship)
        2. Graduate Program / Entry-Level (if graduate program/entry level terms found)
        3. Generative AI / Applied AI / ML / NLP / Backend (based on technical terms)
        4. Remote (if remote flag is True)
        5. FinTech / Healthcare AI (based on industry keywords)
        6. Startup (if company size is small or mentions startup/scale-up)
        7. Enterprise (Default fallback)
        """
        title = job.get("job", {}).get("job_title", "").lower()
        desc = job.get("job", {}).get("job_description", "").lower()
        c_size = str(job.get("company", {}).get("company_size", "")).lower()
        industry = job.get("company", {}).get("company_industry", "").lower()
        is_remote = job.get("location", {}).get("remote", False)

        # 1. Internship
        if "intern" in title or "internship" in title or "intern" in desc:
            return "Internship"

        # 2. Graduate / Entry Level
        if any(w in title or w in desc for w in ["graduate program", "rotational", "fellowship"]):
            return "Graduate Program"
        if any(w in title for w in ["entry-level", "junior", "associate"]):
            return "Entry-Level"

        # 3. Technical Domains
        if any(w in desc for w in ["generative ai", "llm", "rag", "langchain", "prompt engineering"]):
            return "Generative AI"
        if any(w in desc for w in ["natural language processing", "nlp", "text mining", "spacy"]):
            return "NLP"
        if any(w in desc for w in ["pytorch", "tensorflow", "scikit-learn", "machine learning", "training pipeline"]):
            return "ML"
        if any(w in desc for w in ["artificial intelligence", "ai agent", "predictive model"]):
            return "Applied AI"
        if any(w in desc for w in ["backend", "fastapi", "django", "flask", "database", "api design"]):
            return "Backend"

        # 4. Remote
        if is_remote:
            return "Remote"

        # 5. Industries
        if any(w in industry or w in desc for w in ["finance", "fintech", "banking", "wealth", "trading"]):
            return "FinTech"
        if any(w in industry or w in desc for w in ["healthcare", "medical", "biotech", "pharma", "patient"]):
            return "Healthcare AI"

        # 6. Startup vs Enterprise
        if "1-10" in c_size or "11-50" in c_size or "startup" in desc or "scale-up" in desc:
            return "Startup"

        return "Enterprise"
