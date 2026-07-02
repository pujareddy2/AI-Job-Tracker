"""
application_assistant/notifier.py — Outreach notifications for missing details
=============================================================================
Purpose
-------
Alerts the candidate via SMTP email when fields are missing or an application
is ready for submission approval.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from config import settings
from utils.logger import get_logger

logger = get_logger("assistant_notifier")


class AssistantNotifier:
    """Manages notifications regarding application flow stages."""

    @staticmethod
    def send_missing_info_email(
        job_title: str,
        company_name: str,
        missing_fields: list[str],
        job_uuid: str | None = None,
        recipient: str | None = None,
    ) -> bool:
        """Send an email requesting missing application fields with HTML button alternative."""
        sender = settings.email_address
        password = settings.email_password
        target_email = recipient or sender

        if not sender or not password:
            logger.error("SMTP credentials missing. Logging notification instead.")
            logger.info(f"NOTIFICATION MOCK: Missing fields for {job_title} @ {company_name}: {missing_fields}")
            return False

        apply_url = "https://docs.google.com/spreadsheets/d/" + (settings.google_sheet_id or "")
        if job_uuid:
            try:
                import json
                from pathlib import Path
                jobs_file = Path(settings.cache_dir) / "deduplicated_jobs.json"
                if jobs_file.exists():
                    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
                    for j in jobs:
                        if j.get("identity", {}).get("uuid") == job_uuid:
                            apply_url = j.get("application", {}).get("application_url") or apply_url
                            break
            except Exception:
                pass

        msg = EmailMessage()
        msg["Subject"] = f"Action Required: Missing Info for {job_title} @ {company_name}"
        msg["From"] = sender
        msg["To"] = target_email

        body = (
            f"Hello,\n\nThe AI Job Application Assistant is preparing your application for:\n"
            f"Role: {job_title}\nCompany: {company_name}\n\n"
            f"The following required fields are missing from your profile:\n"
            f"{', '.join(missing_fields)}\n\n"
            f"Please update these details or visit {apply_url} to check requirements.\n\n"
            f"Best regards,\nAI Career Assistant"
        )
        msg.set_content(body)

        missing_items_html = "".join([f"<li style='color: #f87171; font-weight: 500; font-size: 13px; margin-bottom: 4px;'>❌ {field} (Missing)</li>" for field in missing_fields])
        
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f1f5f9; padding: 20px; margin: 0; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
    h2 {{ color: #38bdf8; margin-top: 0; font-size: 20px; font-weight: 700; }}
    p {{ font-size: 14px; line-height: 1.6; color: #cbd5e1; }}
    .btn {{ display: inline-block; background-color: #0ea5e9; color: #ffffff !important; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; text-align: center; margin-top: 15px; border: none; cursor: pointer; }}
    .btn:hover {{ background-color: #0284c7; }}
    .footer {{ margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; font-size: 12px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
<div class="card">
    <h2>🛠️ Action Required: Missing Information</h2>
    <p>The AI Job Application Assistant is preparing your application for:</p>
    <p><strong>Role:</strong> {job_title}<br><strong>Company:</strong> {company_name}</p>
    
    <p style="margin-bottom: 8px; font-weight: 600;">The following required documents/fields are missing from your profile:</p>
    <ul style="list-style: none; padding: 0; margin: 0 0 16px 0;">
        {missing_items_html}
    </ul>
    
    <p>Please click the button below to check requirements on the job site and update your application details:</p>
    <a href="{apply_url}" class="btn" target="_blank">🔍 Go to Listing & Check Requirements</a>
    
    <div class="footer">
        <p>AI Career Operating System &copy; 2026</p>
    </div>
</div>
</body>
</html>"""
        msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            logger.info(f"Sent missing info email to {target_email}")
            return True
        except Exception as e:
            logger.exception("Failed to send missing info email.")
            return False

    @staticmethod
    def send_approval_request_email(
        job_title: str,
        company_name: str,
        job_uuid: str | None = None,
        recipient: str | None = None,
    ) -> bool:
        """Send an email requesting application submission approval with HTML button alternative."""
        sender = settings.email_address
        password = settings.email_password
        target_email = recipient or sender

        if not sender or not password:
            logger.error("SMTP credentials missing. Logging approval request instead.")
            logger.info(f"NOTIFICATION MOCK: Approval requested for {job_title} @ {company_name}")
            return False

        uuid_str = job_uuid or ""
        msg = EmailMessage()
        msg["Subject"] = f"Action Required: Approve Application for {job_title} @ {company_name}"
        msg["From"] = sender
        msg["To"] = target_email

        body = (
            f"Hello,\n\nYour application for {job_title} at {company_name} is prefilled and ready to submit.\n\n"
            f"Please approve application submission: http://localhost:8000/api/applications/email/action?action=approve&job_uuid={uuid_str}\n\n"
            f"Best regards,\nAI Career Assistant"
        )
        msg.set_content(body)

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f1f5f9; padding: 20px; margin: 0; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
    h2 {{ color: #10b981; margin-top: 0; font-size: 20px; font-weight: 700; }}
    p {{ font-size: 14px; line-height: 1.6; color: #cbd5e1; }}
    .btn {{ display: inline-block; background-color: #10b981; color: #ffffff !important; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; text-align: center; margin-top: 15px; margin-right: 12px; border: none; cursor: pointer; }}
    .btn:hover {{ background-color: #059669; }}
    .btn-secondary {{ background-color: #475569; color: #ffffff !important; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block; }}
    .btn-secondary:hover {{ background-color: #334155; }}
    .footer {{ margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; font-size: 12px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
<div class="card">
    <h2>🎉 Ready to Apply!</h2>
    <p>Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> is fully prefilled and ready to submit.</p>
    
    <p>You can proceed to apply now or save for later using the direct actions below:</p>
    
    <a href="http://localhost:8000/api/applications/email/action?action=approve&job_uuid={uuid_str}" class="btn" target="_blank">🚀 Apply Now (Prefilled)</a>
    <a href="http://localhost:8000/api/applications/email/action?action=later&job_uuid={uuid_str}" class="btn btn-secondary" target="_blank">⏰ Save For Later</a>
    
    <div class="footer">
        <p>AI Career Operating System &copy; 2026</p>
    </div>
</div>
</body>
</html>"""
        msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            logger.info(f"Sent approval request email to {target_email}")
            return True
        except Exception as e:
            logger.exception("Failed to send approval request email.")
            return False
