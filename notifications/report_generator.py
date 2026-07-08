"""
notifications/report_generator.py — HTML Career Report Generator
================================================================
Purpose
-------
Aggregates job data, computes insights (top jobs, skills gap, new companies),
and renders a responsive HTML email report using Jinja2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from config import settings

from jinja2 import Environment, FileSystemLoader

from job_model.universal_model import UniversalJobModel


class ReportGenerator:
    """
    Analyzes job results and generates an HTML report.
    """

    def __init__(self) -> None:
        """Initialize the Jinja2 environment."""
        self.template_dir = Path(__file__).resolve().parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
        )

    def _get_top_jobs(self, jobs: list[UniversalJobModel], limit: int = 10) -> list[UniversalJobModel]:
        """Return the top jobs sorted primarily by confidence score."""
        
        def sort_key(job: UniversalJobModel) -> float:
            return job.confidence.overall_score

        sorted_jobs = sorted(jobs, key=sort_key, reverse=True)
        return sorted_jobs[:limit]

    def _get_ppo_internships(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        """Return all internships that mention a PPO/Return Offer."""
        internships = []
        for job in jobs:
            if job.internship.is_internship:
                if job.internship.ppo_available or (job.internship.ppo_probability and job.internship.ppo_probability.lower() in ["high", "medium"]):
                    internships.append(job)
        return internships

    def _get_skills_gap(self, jobs: list[UniversalJobModel]) -> list[dict[str, Any]]:
        """
        Analyze the top jobs to find the most commonly missing skills.
        Returns a sorted list of dictionaries with skill and frequency.
        """
        gap_freq: dict[str, int] = {}
        for job in jobs:
            for skill in job.resume_match.resume_keywords_missing:
                gap_freq[skill] = gap_freq.get(skill, 0) + 1
                
        sorted_gaps = sorted(gap_freq.items(), key=lambda item: item[1], reverse=True)
        return [{"skill": k, "count": v} for k, v in sorted_gaps[:10]]

    def generate_html_report(self, jobs: list[UniversalJobModel]) -> str:
        """
        Build the context and render the Jinja2 HTML template.
        """
        if not jobs:
            return ""

        top_jobs = self._get_top_jobs(jobs)
        ppo_internships = self._get_ppo_internships(jobs)
        skills_gap = self._get_skills_gap(top_jobs)

        # Attach application assistant state to each job dynamically
        from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
        orch = ApplicationWorkflowOrchestrator()
        for j in jobs:
            try:
                state = orch.load_state(j.identity.uuid)
                if state:
                    setattr(j, "assistant_state", state)
            except Exception:
                pass

        # Context for the template
        context = {
            "total_jobs": len(jobs),
            "top_jobs": top_jobs,
            "ppo_internships": ppo_internships,
            "skills_gap": skills_gap,
            "date": jobs[0].metadata.discovered_date.split("T")[0] if jobs else "",
            "sheet_id": settings.google_sheet_id,
        }

        template = self.env.get_template("career_report.html")
        return template.render(context)

    def generate_csv_report(self, jobs: list[UniversalJobModel]) -> bytes:
        """Generate a CSV report of the jobs."""
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date Found", "Company", "Role", "Confidence Score", "Grade", "Category", "Reason", "Apply Link"])
        for job in jobs:
            writer.writerow([
                job.metadata.discovered_date.split("T")[0] if job.metadata.discovered_date else "",
                job.company.company_name,
                job.job.job_title,
                f"{job.confidence.overall_score}%",
                job.confidence.grade,
                job.confidence.category,
                job.confidence.reason,
                job.application.application_url
            ])
        return output.getvalue().encode("utf-8")

    def generate_json_report(self, jobs: list[UniversalJobModel]) -> bytes:
        """Generate a JSON report of the jobs."""
        import json
        return json.dumps([j.to_dict() for j in jobs], indent=2).encode("utf-8")

    def generate_pdf_report(self, jobs: list[UniversalJobModel]) -> bytes:
        """Generate a ReportLab PDF summary report."""
        import io
        from datetime import date
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
        )
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=10,
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            "SubtitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=25
        )
        section_style = ParagraphStyle(
            "SectionStyle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#2C5282"),
            spaceBefore=12,
            spaceAfter=6
        )

        story.append(Paragraph("AI Career Operating System - Daily Digest", title_style))
        today_str = date.today().isoformat()
        story.append(Paragraph(f"Generated on {today_str} | Candidate: Puja Midde", subtitle_style))

        # Dashboard Summary Section
        story.append(Paragraph("Dashboard Summary", section_style))
        total = len(jobs)
        manual_review = len([j for j in jobs if j.application.status == "Needs Manual Review"])
        auto_accepted = total - manual_review
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Opportunities Analyzed", str(total)],
            ["Automatically Approved (High Confidence)", str(auto_accepted)],
            ["Routed to Manual Review (Unclear Eligibility / Match)", str(manual_review)],
        ]
        t_summary = Table(summary_data, colWidths=[280, 100])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 15))

        # Top Recommended Jobs
        story.append(Paragraph("Top Recommended Opportunities", section_style))
        top_jobs = sorted(jobs, key=lambda j: j.confidence.overall_score, reverse=True)[:5]
        job_data = [["Company", "Role", "Confidence", "Category"]]
        for job in top_jobs:
            job_data.append([
                job.company.company_name,
                job.job.job_title,
                f"{job.confidence.overall_score}%",
                job.confidence.category
            ])
        t_jobs = Table(job_data, colWidths=[110, 180, 50, 90])
        t_jobs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C5282")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ]))
        story.append(t_jobs)
        story.append(Spacer(1, 15))

        # PPO Internships Section
        ppo_interns = self._get_ppo_internships(jobs)[:5]
        if ppo_interns:
            story.append(Paragraph("Top PPO Internships (Conversion Offer Explicitly Mentioned)", section_style))
            ppo_data = [["Company", "Role", "PPO Probability"]]
            for job in ppo_interns:
                ppo_data.append([
                    job.company.company_name,
                    job.job.job_title,
                    job.internship.ppo_probability or "High"
                ])
            t_ppo = Table(ppo_data, colWidths=[150, 200, 80])
            t_ppo.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#319795")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
            ]))
            story.append(t_ppo)
            story.append(Spacer(1, 15))

        # Skill Gaps
        skills_gap = self._get_skills_gap(top_jobs)
        if skills_gap:
            story.append(Paragraph("Identified Skill Gaps (Top Missing Keywords)", section_style))
            sg_data = [["Missing Skill / Keyword", "Frequency across Top Jobs"]]
            for gap in skills_gap[:5]:
                sg_data.append([gap["skill"], f"{gap['count']} jobs"])
            t_sg = Table(sg_data, colWidths=[250, 180])
            t_sg.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#805AD5")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
            ]))
            story.append(t_sg)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
