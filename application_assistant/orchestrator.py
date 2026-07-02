"""
application_assistant/orchestrator.py — Event Orchestrator and State Machine
=============================================================================
Purpose
-------
Manages transitions of application workflows. Integrates with the ResumeMonitor
to trigger down-stream matching updates when a resume changes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from application_assistant.config import DEFAULT_ASSISTANT_CONFIG, AssistantConfig
from application_assistant.form_filler import ApplicationFormFiller
from application_assistant.models import ApplicationState, StateTransition
from application_assistant.notifier import AssistantNotifier
from utils.logger import get_logger

logger = get_logger("application_orchestrator")


class ApplicationWorkflowOrchestrator:
    """Manages application state transitions and sheet synchronizations."""

    def __init__(self, config: AssistantConfig | None = None) -> None:
        self.config = config or DEFAULT_ASSISTANT_CONFIG
        self.states_dir = self.config.states_dir
        self.form_filler = ApplicationFormFiller(self.config)

    def load_state(self, job_uuid: str) -> ApplicationState | None:
        """Load persistent application state from cache."""
        path = self.states_dir / f"{job_uuid[:16]}_state.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ApplicationState.model_validate(data)
        except Exception as exc:
            logger.warning(f"Failed to load application state for {job_uuid}: {exc}")
            return None

    def save_state(self, state: ApplicationState) -> None:
        """Save application state to cache."""
        self.states_dir.mkdir(parents=True, exist_ok=True)
        path = self.states_dir / f"{state.job_uuid[:16]}_state.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    # ── State Machine Transitions ──────────────────────────────────────────

    def start_application(
        self,
        profile: dict[str, Any],
        job: dict[str, Any],
        resume_version: str,
    ) -> ApplicationState:
        """Initialize or resume an application preparation flow."""
        job_uuid = job.get("identity", {}).get("uuid", "unknown")
        job_title = job.get("job", {}).get("job_title", "Unknown Role")
        company_name = job.get("company", {}).get("company_name", "Unknown Company")

        state = self.load_state(job_uuid)
        now = datetime.now().isoformat()

        if not state:
            state = ApplicationState(
                job_uuid=job_uuid,
                job_title=job_title,
                company_name=company_name,
                state="Prepared",
                resume_version_used=resume_version,
                last_transition_time=now
            )
            state.history.append(StateTransition(
                from_state="None",
                to_state="Prepared",
                timestamp=now,
                reason="Application workflow initialized."
            ))

        # Prefill form and check missing
        filled, missing = self.form_filler.prefill_form(profile)
        state.filled_fields = filled
        state.missing_fields = missing

        # Run readiness audit
        audit = self.form_filler.audit_application_readiness(profile)
        state.readiness_score = audit["readiness_score"]
        state.missing_documents = audit["missing_documents"]
        state.required_documents = audit["required_documents"]

        # Generate outreach templates matching company & role
        candidate = profile.get("personal", {}).get("name", "Puja Midde")
        state.cover_letter = (
            f"Dear Hiring Team at {company_name},\n\n"
            f"I am writing to express my enthusiastic interest in the {job_title} position. "
            f"With my strong background in Python, FastAPI, and Agentic AI/LLM technologies, "
            f"I am confident in my ability to contribute effectively to your engineering team. "
            f"I look forward to the possibility of discussing how my skills align with your needs.\n\n"
            f"Sincerely,\n{candidate}"
        )
        
        state.recruiter_email_draft = (
            f"Subject: Interest in {job_title} role - {candidate}\n\n"
            f"Dear Recruiter,\n\n"
            f"I recently applied for the {job_title} position at {company_name} and wanted to reach out directly. "
            f"Given my specialization in Python backend development and Generative AI systems, "
            f"I believe I would be a great fit for your team. "
            f"Please let me know if we can schedule a brief chat.\n\n"
            f"Best regards,\n{candidate}"
        )
        
        state.linkedin_message = (
            f"Hi, I saw your team at {company_name} is hiring for a {job_title}. "
            f"I have strong experience with Python, FastAPI, RAG, and LLM development. "
            f"I would love to connect and learn more about this opportunity!"
        )
        
        state.cold_email = (
            f"Subject: Technical Contribution / {job_title} Role at {company_name}\n\n"
            f"Dear Lead Engineer,\n\n"
            f"I've been following {company_name}'s work and wanted to reach out. "
            f"I'm an incoming 2027 graduate specializing in Python backend and AI Agent systems. "
            f"I've built robust FastAPI APIs and custom RAG agents, and I'd love to bring this expertise to your team as a {job_title}.\n\n"
            f"Best,\n{candidate}"
        )
        
        state.outreach_notes = (
            f"Preparation Suggestions for {job_title} at {company_name}:\n"
            f"- Review core python concepts, concurrency, and API performance.\n"
            f"- Be prepared to discuss RAG architecture, vector databases, and LLM integration.\n"
            f"- Research {company_name}'s recent announcements and product updates."
        )

        job_uuid = job.get("identity", {}).get("uuid")
        if missing:
            state.readiness_label = "Needs Information"
            state.recommended_actions = ["Provide missing details to complete application"]
            self._transition(state, "Waiting for Information", f"Missing required fields: {missing}")
            AssistantNotifier.send_missing_info_email(job_title, company_name, missing, job_uuid)
        else:
            state.readiness_label = "Ready"
            state.recommended_actions = ["Approve submission for this job"]
            self._transition(state, "Waiting for Approval", "All required fields prefilled. Pending approval.")
            AssistantNotifier.send_approval_request_email(job_title, company_name, job_uuid)

        self.save_state(state)
        return state

    def provide_missing_information(
        self,
        job_uuid: str,
        profile: dict[str, Any],
        custom_inputs: dict[str, str],
    ) -> ApplicationState:
        """Provide custom inputs to resolve missing fields."""
        state = self.load_state(job_uuid)
        if not state:
            raise ValueError(f"State not found for job: {job_uuid}")

        now = datetime.now().isoformat()
        filled, missing = self.form_filler.prefill_form(profile, custom_inputs)
        
        state.filled_fields.update(filled)
        state.missing_fields = missing

        # Run readiness audit with custom inputs
        audit = self.form_filler.audit_application_readiness(profile, custom_inputs)
        state.readiness_score = audit["readiness_score"]
        state.missing_documents = audit["missing_documents"]
        state.required_documents = audit["required_documents"]

        # Re-inject document drafts if newly provided
        if "Cover Letter" in custom_inputs or "cover_letter" in custom_inputs:
            state.cover_letter = custom_inputs.get("Cover Letter") or custom_inputs.get("cover_letter")

        if missing:
            state.readiness_label = "Needs Information"
            state.recommended_actions = ["Provide missing details to complete application"]
            self._transition(state, "Waiting for Information", f"Still missing: {missing}")
        else:
            state.readiness_label = "Ready"
            state.recommended_actions = ["Approve submission for this job"]
            self._transition(state, "Waiting for Approval", "All missing fields resolved. Pending approval.")
            AssistantNotifier.send_approval_request_email(state.job_title, state.company_name, state.job_uuid)

        self.save_state(state)
        return state

    def approve_application(self, job_uuid: str) -> ApplicationState:
        """Explicitly authorize and submit the job application."""
        state = self.load_state(job_uuid)
        if not state:
            raise ValueError(f"State not found for job: {job_uuid}")

        if state.state != "Waiting for Approval":
            raise ValueError(f"Application cannot be approved from state: {state.state}")

        # Transition to Submitted
        self._transition(state, "Submitted", "User granted explicit submission approval.")
        
        # Save manual status update to cache/manual_applications.json
        manual_apps_path = self.config.manual_apps_path
        manual_apps = {}
        if manual_apps_path.exists():
            try:
                manual_apps = json.loads(manual_apps_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        manual_apps[job_uuid] = "Applied"
        manual_apps_path.write_text(json.dumps(manual_apps, indent=2), encoding="utf-8")

        self.save_state(state)
        return state

    # ── Downstream Orchestration Triggers ──────────────────────────────────

    def handle_resume_change(
        self,
        profile_builder_fn: Any,
        matching_engine_fn: Any,
    ) -> None:
        """
        Triggers Candidate Profile regeneration and matching engines
        when a resume change is observed.
        """
        logger.info("Resume change detected. Triggering down-stream updates...")
        try:
            profile_builder_fn()
            matching_engine_fn()
            logger.info("Regeneration and re-matching completed.")
        except Exception as exc:
            logger.error(f"Failed to complete downstream matching stages: {exc}")

    # ── Internal Transition Logger ─────────────────────────────────────────

    def _transition(self, state: ApplicationState, to: str, reason: str) -> None:
        now = datetime.now().isoformat()
        state.history.append(StateTransition(
            from_state=state.state,
            to_state=to,
            timestamp=now,
            reason=reason
        ))
        state.state = to
        state.last_transition_time = now
        logger.info(f"Application {state.job_uuid[:8]} transitioned from {state.history[-1].from_state} to {to}: {reason}")
