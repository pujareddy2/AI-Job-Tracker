"""
communication_engine/engine.py — Orchestrator for outreach document generation
==============================================================================
Purpose
-------
Orchestrates the template matching, personalization, quality validation,
and export formatting for Cover Letters, emails, LinkedIn requests, and follow-ups.

Design Decisions
----------------
- Safe context lookup from CandidateProfile.
- Iterative generation across 4 tone profiles.
- Automated validation of spelling, placeholders, and truthfulness.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings, PROJECT_ROOT
from communication_engine.config import DEFAULT_COMMUNICATION_CONFIG, CommunicationConfig
from communication_engine.exporter import DocumentExporter
from communication_engine.models import GeneratedDocument, JobCommunicationReport, QualityScoreCard
from communication_engine.personalization import PersonalizationEngine
from communication_engine.quality_validator import QualityValidator
from communication_engine.templates import COVER_LETTER_TEMPLATES, TemplateSelector, modify_tone
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Internal Template Registries for non-cover-letter documents ────────────
EMAIL_TEMPLATES = {
    "Application Email": (
        "Dear Hiring Team at {company_name},\n\n"
        "I am writing to apply for the {job_title} position. As an engineering graduate from {institution} with a CGPA of {cgpa}, "
        "I have built {projects_paragraph} and am highly proficient in {skills_paragraph}.\n\n"
        "{internships_paragraph}\n\n"
        "My resume is attached, and you can view my portfolio at {candidate_portfolio} and coding profiles at {candidate_github}. "
        "I would welcome the opportunity to discuss how I can contribute to your engineering standards.\n\n"
        "Sincerely,\n{candidate_name}\n{candidate_email} | {candidate_phone}"
    ),
    "Cold Email": (
        "Dear Hiring Team,\n\n"
        "I hope this email finds you well. I am contacting you regarding potential opportunities on your engineering team at {company_name}. "
        "I recently graduated from {institution} with a CGPA of {cgpa} in {branch}.\n\n"
        "I specialize in {skills_paragraph} and completed projects like {projects_paragraph}. My portfolio is available at {candidate_portfolio} "
        "and GitHub is {candidate_github}.\n\n"
        "I have attached my resume and would appreciate a brief chat to introduce myself. Thank you for your time.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "LinkedIn Connection Request": (
        "Hi Team at {company_name}, I'm a software engineer specializing in {skills_paragraph}. "
        "I've been following your work and would love to connect. Best, {candidate_name}."
    ),
    "LinkedIn Connection Accepted": (
        "Hi, thanks for connecting! I'm highly interested in engineering at {company_name} and would love to stay in touch "
        "as opportunities arise. Best, {candidate_name}."
    ),
    "LinkedIn Application Follow-up": (
        "Hi, I recently applied for the {job_title} role. I wanted to highlight my background in {skills_paragraph} "
        "and projects like {projects_paragraph}. Thanks, {candidate_name}."
    ),
    "LinkedIn Interview Follow-up": (
        "Hi, thank you for the interview yesterday. I really enjoyed discussing the engineering challenges at {company_name}. "
        "Best, {candidate_name}."
    ),
    "LinkedIn Thank-you Message": (
        "Hi, thanks again for the chat. I'm excited about the possibility of joining {company_name}. Best, {candidate_name}."
    ),
    "Recruiter Follow-up Email": (
        "Dear Hiring Team,\n\n"
        "I wanted to follow up on my application for the {job_title} role. I remain highly interested in {company_name} "
        "and wanted to check if there are any updates regarding the next steps.\n\n"
        "Thank you for your time and guidance.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Application Follow-up Email": (
        "Dear Hiring Team,\n\n"
        "I hope you are having a productive week. I am following up on my application for the {job_title} role at {company_name}. "
        "I wanted to reiterate my enthusiasm and confirm if any additional details are needed from my end.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Thank-you Email": (
        "Dear Hiring Team,\n\n"
        "Thank you for the opportunity to interview for the {job_title} role yesterday. I really enjoyed learning more about "
        "{company_name}'s technical goals and engineering culture.\n\n"
        "Our discussion confirmed my enthusiasm for the role and my confidence that my skills in {skills_paragraph} "
        "will allow me to contribute effectively. Please let me know if you need any further information.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Interview Confirmation Email": (
        "Dear Hiring Team,\n\n"
        "Thank you for scheduling the interview. I am writing to confirm my availability for the interview for the "
        "{job_title} position. I look forward to speaking with the team.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
    "Offer Acceptance": (
        "Dear Hiring Team,\n\n"
        "I am thrilled to accept your offer for the {job_title} position at {company_name}. Thank you for this opportunity. "
        "I am excited to join the team and contribute to your products.\n\n"
        "I look forward to completing the onboarding process. Please let me know the next steps.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Offer Clarification": (
        "Dear Hiring Team,\n\n"
        "Thank you for extending the offer for the {job_title} position. I am highly excited about joining {company_name}.\n\n"
        "Before finalizing the agreement, I wanted to clarify a few details regarding the work arrangement, starting date, "
        "and location options. I look forward to your guidance.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Offer Negotiation": (
        "Dear Hiring Team,\n\n"
        "Thank you very much for the offer for the {job_title} role. I am excited about the opportunity to join {company_name}.\n\n"
        "Based on my technical background and projects like {projects_paragraph}, I would like to discuss the possibility of "
        "adjusting the base compensation package to align with market rates. I am open to discussing this and look forward "
        "to your thoughts.\n\n"
        "Best regards,\n{candidate_name}"
    ),
    "Application Withdrawal": (
        "Dear Hiring Team,\n\n"
        "I am writing to respectfully withdraw my application for the {job_title} position. I have recently accepted another offer.\n\n"
        "Thank you very much for your time and consideration during this process.\n\n"
        "Sincerely,\n{candidate_name}"
    ),
}

EMAIL_SUBJECTS = {
    "Application Email": "Application for {job_title} - {candidate_name}",
    "Cold Email": "Outreach from Software Engineer - {candidate_name}",
    "Recruiter Follow-up Email": "Follow-up: {job_title} application - {candidate_name}",
    "Application Follow-up Email": "Checking in: {job_title} application status - {candidate_name}",
    "Thank-you Email": "Thank you - {job_title} Interview - {candidate_name}",
    "Interview Confirmation Email": "Confirmation: {job_title} Interview - {candidate_name}",
    "Offer Acceptance": "Offer Acceptance: {job_title} - {candidate_name}",
    "Offer Clarification": "Clarification: {job_title} offer details - {candidate_name}",
    "Offer Negotiation": "Discussion: {job_title} offer - {candidate_name}",
    "Application Withdrawal": "Application Withdrawal: {job_title} - {candidate_name}",
}


class CommunicationEngine:
    """Orchestrates communication generation, scoring, and multi-format exports."""

    def __init__(self, config: CommunicationConfig | None = None) -> None:
        self.config = config or DEFAULT_COMMUNICATION_CONFIG
        self.validator = QualityValidator(self.config.quality_weights)
        self.output_dir = PROJECT_ROOT / self.config.output_dir

    def load_profile(self) -> dict[str, Any]:
        """Loads candidate profile cached json."""
        profile_path = settings.cache_dir / "candidate_profile.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"CandidateProfile not found at {profile_path}")
        return json.loads(profile_path.read_text(encoding="utf-8"))

    def generate_outreach_for_job(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
        tone_override: str | None = None,
    ) -> JobCommunicationReport:
        """
        Generate all 13 communication documents for a job opportunity.
        """
        job_id = job.get("identity", {}).get("uuid", "unknown")
        job_title = job.get("job", {}).get("job_title", "Software Engineer")
        company_name = job.get("company", {}).get("company_name", "your company")

        logger.info(f"Generating outreach suite for: {job_title} @ {company_name}")

        # 1. Resolve Best Template Category
        template_category = TemplateSelector.select_template(job)
        logger.info(f"Selected template category: {template_category}")

        # 2. Build personalization context dictionary
        context = PersonalizationEngine.build_context(profile, job)

        # Output folder path
        export_dir = self.output_dir / job_id[:16]
        export_dir.mkdir(parents=True, exist_ok=True)

        generated_docs = []
        target_tone = tone_override or self.config.default_tone
        t0 = datetime.now().isoformat()

        # ── 3. Generate Cover Letter ──────────────────────────────────────────
        base_cl_template = COVER_LETTER_TEMPLATES.get(template_category, COVER_LETTER_TEMPLATES["Enterprise"])
        cl_body = base_cl_template.format(**context)
        cl_body = modify_tone(cl_body, target_tone)

        # Validate Cover Letter
        cl_scorecard = self.validator.validate(
            "Cover Letter", cl_body, profile, company_name, job_title
        )

        cl_doc = GeneratedDocument(
            document_type="Cover Letter",
            tone=target_tone,
            subject=None,
            body=cl_body,
            template_name=template_category,
            quality_scorecard=cl_scorecard,
            generated_at=t0,
        )
        generated_docs.append(cl_doc)

        # Export Cover Letter
        DocumentExporter.export(
            "Cover Letter", target_tone, None, cl_body, export_dir, self.config.default_export_formats
        )

        # ── 4. Generate other 12 communication items ──────────────────────────
        for doc_type, base_template in EMAIL_TEMPLATES.items():
            subject_tmpl = EMAIL_SUBJECTS.get(doc_type)
            subject = subject_tmpl.format(**context) if subject_tmpl else None
            
            body = base_template.format(**context)
            body = modify_tone(body, target_tone)

            # Validate document
            scorecard = self.validator.validate(
                doc_type, body, profile, company_name, job_title
            )

            g_doc = GeneratedDocument(
                document_type=doc_type,
                tone=target_tone,
                subject=subject,
                body=body,
                template_name="Standard",
                quality_scorecard=scorecard,
                generated_at=t0,
            )
            generated_docs.append(g_doc)

            # Export document
            DocumentExporter.export(
                doc_type, target_tone, subject, body, export_dir, self.config.default_export_formats
            )

        report = JobCommunicationReport(
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            documents=generated_docs,
            export_directory=str(export_dir),
        )

        # Save JSON metadata report
        report_json_path = export_dir / "communication_report.json"
        report_json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        
        logger.info(f"Generated and exported 13 documents to {export_dir}")
        return report
