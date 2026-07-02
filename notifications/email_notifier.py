"""
notifications/email_notifier.py — Email Notification Adapter
============================================================
Purpose
-------
Send job alert emails via Gmail SMTP.

Responsibilities (Phase 10)
---------------------------
- Connect to Gmail SMTP (smtp.gmail.com:587) using TLS.
- Authenticate with settings.email_address and settings.email_password.
- Render the HTML email summarising new job listings.
- Handle SMTP errors gracefully and abort if no valid jobs or only duplicates.
"""

from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from typing import Any

from config import settings
from utils.logger import get_logger
from utils.exceptions import EmailError
from notifications.base import Notifier
from notifications.report_generator import ReportGenerator
from job_model.universal_model import UniversalJobModel


class EmailNotifier(Notifier):
    """
    Sends job alert emails via Gmail SMTP.
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.report_generator = ReportGenerator()
        self.max_attempts = 3
        self.smtp_timeout = 60

    def _send_message(self, msg: EmailMessage, recipient: str) -> None:
        """
        Send an email with retries and a Gmail SSL fallback.

        Gmail occasionally closes STARTTLS connections during DATA transfer,
        especially when attachments are involved. Retrying on a new connection
        and then falling back to SMTP_SSL makes the notification path much less
        fragile without changing caller behavior.
        """
        sender = settings.email_address
        password = settings.email_password
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=self.smtp_timeout) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(sender, password)
                    server.send_message(msg)
                return
            except (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                smtplib.SMTPDataError,
                TimeoutError,
                OSError,
            ) as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    wait_s = 2 ** attempt
                    self.logger.warning(
                        "SMTP STARTTLS attempt %d/%d failed for %s; retrying in %ss: %s",
                        attempt,
                        self.max_attempts,
                        recipient,
                        wait_s,
                        exc,
                    )
                    time.sleep(wait_s)
                    continue
                break
            except smtplib.SMTPException:
                raise

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=self.smtp_timeout) as server:
                server.login(sender, password)
                server.send_message(msg)
            return
        except Exception as exc:
            if last_error is not None:
                raise EmailError(f"SMTP error after retries: {last_error}; SSL fallback: {exc}") from exc
            raise EmailError(f"SMTP error: {exc}") from exc

    def send_report(self, jobs: list[UniversalJobModel], **kwargs: Any) -> bool:
        """
        Compose and send a job digest email.
        """
        self.logger.info("EmailNotifier triggered to send job report.")

        sender = settings.email_address
        password = settings.email_password
        recipient = kwargs.get("recipient", sender)

        if not sender or not password:
            self.logger.error("Email credentials are not configured in settings. Aborting.")
            return False

        if not jobs:
            self.logger.warning("No jobs provided. Sending empty-results email.")
            return self.send_empty_results_report(
                reason="The pipeline completed, but all discovered jobs were rejected by filters.",
                recipient=recipient,
            )

        # Filter out duplicates or expired jobs entirely if they are the only ones
        meaningful_jobs = [j for j in jobs if not (j.reliability.duplicate or j.reliability.expired)]
        if not meaningful_jobs:
            self.logger.warning("Only duplicates or expired jobs found. Sending empty-results email.")
            return self.send_empty_results_report(
                reason="The pipeline found jobs, but every result was duplicate or expired.",
                recipient=recipient,
            )

        try:
            html_content = self.report_generator.generate_html_report(meaningful_jobs)
            csv_data = self.report_generator.generate_csv_report(meaningful_jobs)
            json_data = self.report_generator.generate_json_report(meaningful_jobs)
            pdf_data = self.report_generator.generate_pdf_report(meaningful_jobs)
        except Exception as e:
            self.logger.exception(f"Failed to generate reports or attachments: {e}")
            return False

        msg = EmailMessage()
        msg["Subject"] = f"AI Career Assistant - Daily Report ({len(meaningful_jobs)} Jobs)"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content("Please view this email in an HTML-compatible client.")
        msg.add_alternative(html_content, subtype="html")

        # Attach reports
        msg.add_attachment(csv_data, filename="jobs_report.csv", maintype="text", subtype="csv")
        msg.add_attachment(json_data, filename="jobs_report.json", maintype="application", subtype="json")
        msg.add_attachment(pdf_data, filename="career_report_summary.pdf", maintype="application", subtype="pdf")

        try:
            self._send_message(msg, recipient)
            self.logger.info(f"Successfully sent job alert email to {recipient}")
            return True
        except Exception as e:
            self.logger.exception("Failed to send email via SMTP.")
            raise EmailError(f"SMTP error: {e}") from e

    def send_empty_results_report(self, reason: str, **kwargs: Any) -> bool:
        """Send a completion email even when no jobs survived filtering."""
        sender = settings.email_address
        password = settings.email_password
        recipient = kwargs.get("recipient", sender)

        if not sender or not password:
            self.logger.warning("Email credentials missing - cannot send empty-results report.")
            return False

        body = (
            "AI Job Tracker - Daily Run Completed\n"
            "====================================\n\n"
            "No jobs were sent in today's career report.\n\n"
            f"Reason: {reason}\n\n"
            "What this usually means:\n"
            "- Real jobs were discovered, but filters were too strict.\n"
            "- Location, role, domain, or technology filters rejected the final set.\n"
            "- The tracker avoided sending mock/search-page results.\n\n"
            "Check logs/app.log for stage counts and cache/rejected_jobs.json for rejection reasons.\n"
        )

        msg = EmailMessage()
        msg["Subject"] = "AI Career Assistant - Daily Report (0 Jobs)"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)

        try:
            self._send_message(msg, recipient)
            self.logger.info("Empty-results email sent to %s", recipient)
            return True
        except Exception as exc:
            self.logger.error("Failed to send empty-results email: %s", exc)
            return False

    def send_error_report(self, error_info: dict, **kwargs) -> bool:
        """
        Send a plain-text pipeline failure summary email.

        Called by the orchestrator when the pipeline fails so the user
        is always notified, even if no jobs were collected.

        Parameters
        ----------
        error_info : dict
            Classification dict produced by PipelineError.classify().
        """
        sender = settings.email_address
        password = settings.email_password
        recipient = kwargs.get("recipient", sender)

        if not sender or not password:
            self.logger.warning("Email credentials missing — cannot send error report.")
            return False

        error_type = error_info.get("error_type", "Unknown Error")
        message = error_info.get("message", "No details available.")
        resolution = error_info.get("resolution", "Check the logs for more information.")

        body = (
            f"AI Job Tracker – Pipeline Failure Report\n"
            f"{'=' * 50}\n\n"
            f"Error Type   : {error_type}\n"
            f"Error Details: {message}\n\n"
            f"Suggested Fix: {resolution}\n\n"
            f"Please check the logs/ directory for the full stack trace.\n"
        )

        msg = EmailMessage()
        msg["Subject"] = f"[ACTION REQUIRED] AI Job Tracker Pipeline Failed — {error_type}"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)

        try:
            self._send_message(msg, recipient)
            self.logger.info("Pipeline failure email sent to %s", recipient)
            return True
        except Exception as exc:
            self.logger.error("Failed to send error report email: %s", exc)
            return False

    def send_high_priority_alert(
        self,
        job: UniversalJobModel,
        **kwargs: Any,
    ) -> bool:
        """Send an immediate, real-time alert for a high priority job."""
        sender = settings.email_address
        password = settings.email_password
        recipient = kwargs.get("recipient", sender)

        if not sender or not password:
            self.logger.warning("Email credentials missing — cannot send high priority alert.")
            return False

        try:
            # Generate HTML alert specifically for this job
            html_content = self.report_generator.generate_html_report([job])
            subject = f"🚨 [HIGH PRIORITY] Perfect Match: {job.job.job_title} @ {job.company.company_name}"
        except Exception as e:
            self.logger.exception(f"Failed to generate high priority alert report: {e}")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content("Please view this email in an HTML-compatible client.")
        msg.add_alternative(html_content, subtype="html")

        try:
            self._send_message(msg, recipient)
            self.logger.info(f"Successfully sent high priority job alert to {recipient}")
            return True
        except Exception as exc:
            self.logger.error("Failed to send high priority alert email: %s", exc)
            return False
