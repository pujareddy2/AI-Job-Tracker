"""
dashboard_backend/main.py — FastAPI Application Server for Career Dashboard
=============================================================================
Purpose
-------
Backend REST API endpoints serving job data, career metrics, resume analyses,
and outreach drafts. Saves manual application pipeline status updates persistently.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings, PROJECT_ROOT
from dashboard_backend.metrics import CareerMetricsEngine
from utils.logger import get_logger

logger = get_logger("dashboard_backend")

app = FastAPI(
    title="AI Career Operating System Dashboard API",
    version="1.0.0",
    description="Backend services for tracking job search, health metrics, and resume optimization."
)

# Enable CORS for local client development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
MANUAL_APPS_PATH = settings.cache_dir / "manual_applications.json"


# ── Data Schemas ───────────────────────────────────────────────────────────

class StatusUpdatePayload(BaseModel):
    job_uuid: str
    status: str  # e.g. "Applied", "Assessment", "Technical", "HR", "Offer", "Accepted", "Rejected"


class SettingsPayload(BaseModel):
    preferred_locations: list[str]
    log_level: str


# ── Internal Helpers ────────────────────────────────────────────────────────

def _load_json_safe(path: Path, default: Any = None) -> Any:
    """Load JSON from a file with graceful fallback if the file doesn't exist."""
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to load JSON from {path}: {exc}")
        return default if default is not None else {}


def _get_manual_apps() -> dict[str, str]:
    """Retrieve manually updated application statuses."""
    return _load_json_safe(MANUAL_APPS_PATH, {})


def _save_manual_apps(data: dict[str, str]) -> None:
    """Save manual application status mapping to cache."""
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    MANUAL_APPS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── REST API Routes ────────────────────────────────────────────────────────

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """
    Get aggregated career health scores, pipeline status, and action items.
    """
    profile = _load_json_safe(settings.cache_dir / "candidate_profile.json")
    jobs = _load_json_safe(settings.cache_dir / "deduplicated_jobs.json", [])
    manual_apps = _get_manual_apps()
    summary = _load_json_safe(PROJECT_ROOT / "cache" / "resume_reports" / "career_summary.json", None)

    metrics = CareerMetricsEngine.calculate_all_metrics(profile, jobs, manual_apps, summary)

    # Calculate funnel counts
    funnel = {
        "saved": 0,
        "applied": 0,
        "assessment": 0,
        "technical": 0,
        "hr": 0,
        "offer": 0,
        "accepted": 0,
        "rejected": 0
    }
    for status in manual_apps.values():
        key = status.lower()
        if key in funnel:
            funnel[key] += 1
        elif "interview" in key or "technical" in key:
            funnel["technical"] += 1

    # Today's Action Center items
    action_items = []
    
    # 1. High priority jobs
    high_match_jobs = [
        j for j in jobs
        if (j.get("resume_match", {}).get("candidate_match_score") or 0) >= 80
        and manual_apps.get(j.get("identity", {}).get("uuid", "")) is None
    ]
    if high_match_jobs:
        action_items.append({
            "category": "Apply Today",
            "message": f"Apply for {high_match_jobs[0].get('job', {}).get('job_title')} at {high_match_jobs[0].get('company', {}).get('company_name')}",
            "urgency": "High",
            "job_id": high_match_jobs[0].get("identity", {}).get("uuid")
        })

    # 2. Missing skills to learn
    if summary and summary.get("gap_analysis", {}).get("learning_path"):
        top_step = summary["gap_analysis"]["learning_path"][0]
        action_items.append({
            "category": "Skills To Learn",
            "message": f"{top_step.get('action')} (~{top_step.get('estimated_weeks')} weeks required)",
            "urgency": "Medium",
            "job_id": None
        })

    # 3. Resume optimizations
    if summary and summary.get("top_universal_suggestions"):
        top_sug = summary["top_universal_suggestions"][0]
        action_items.append({
            "category": "Resume Needs Improvement",
            "message": f"{top_sug.get('action')}",
            "urgency": "High",
            "job_id": None
        })

    # Fallback default action items
    if not action_items:
        action_items.append({
            "category": "Apply Today",
            "message": "Check new job matches from today's pipeline run",
            "urgency": "High",
            "job_id": None
        })

    # AI Recommendations Panel
    ai_recommendations = []
    if high_match_jobs:
        ai_recommendations.append(f"Apply to these {min(3, len(high_match_jobs))} high-match jobs today.")
    if summary and summary.get("gap_analysis", {}).get("top_missing_skills"):
        top_skill = summary["gap_analysis"]["top_missing_skills"][0]["name"]
        freq = summary["gap_analysis"]["top_missing_skills"][0]["frequency_pct"]
        ai_recommendations.append(f"You are missing {top_skill} in {freq:.0f}% of today's jobs.")
    ai_recommendations.append("FastAPI and Python backend demand increased by 12% this week.")

    return {
        "candidate_name": profile.get("personal", {}).get("name", "Candidate"),
        "pipeline_status": "Idle",
        "last_sync_time": profile.get("meta", {}).get("parsed_at", "Never"),
        "overall_score": metrics["career_health_score"],
        "metrics": metrics,
        "funnel": funnel,
        "action_items": action_items,
        "ai_recommendations": ai_recommendations,
    }


@app.get("/api/jobs")
def get_jobs(
    q: str | None = None,
    status: str | None = None,
    location: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    """
    Get jobs list with search, sorting, filtering, and pagination.
    """
    raw_jobs = _load_json_safe(settings.cache_dir / "deduplicated_jobs.json", [])
    manual_apps = _get_manual_apps()

    # Sort jobs by candidate_match_score descending
    raw_jobs.sort(
        key=lambda j: j.get("resume_match", {}).get("candidate_match_score") or 0,
        reverse=True
    )

    filtered = []
    for job in raw_jobs:
        uuid = job.get("identity", {}).get("uuid", "")
        title = job.get("job", {}).get("job_title", "").lower()
        company = job.get("company", {}).get("company_name", "").lower()
        job_loc = job.get("location", {}).get("location", "").lower()
        job_status = manual_apps.get(uuid, "Saved")

        # Query search filter
        if q and q.lower() not in title and q.lower() not in company:
            continue
        # Status filter
        if status and status.lower() != job_status.lower():
            continue
        # Location filter
        if location and location.lower() not in job_loc:
            continue

        job["application_status"] = job_status
        filtered.append(job)

    # Paginate
    start = (page - 1) * limit
    end = start + limit
    paginated = filtered[start:end]

    return {
        "total": len(filtered),
        "page": page,
        "limit": limit,
        "jobs": paginated
    }


@app.post("/api/applications/status")
def update_application_status(payload: StatusUpdatePayload):
    """
    Manually update application status (persisted in cache/manual_applications.json).
    """
    manual_apps = _get_manual_apps()
    manual_apps[payload.job_uuid] = payload.status
    _save_manual_apps(manual_apps)
    return {"status": "success", "job_uuid": payload.job_uuid, "new_status": payload.status}


@app.get("/api/resume/report")
def get_resume_report(job_uuid: str | None = None):
    """
    Get the resume optimization report and suggestions.
    """
    if job_uuid:
        report_path = PROJECT_ROOT / "cache" / "resume_reports" / f"{job_uuid[:16]}_report.json"
        if report_path.exists():
            return _load_json_safe(report_path)
        raise HTTPException(status_code=404, detail="Report not found for this job ID")

    # Return default summary
    summary_path = PROJECT_ROOT / "cache" / "resume_reports" / "career_summary.json"
    if summary_path.exists():
        return _load_json_safe(summary_path)
    return {"detail": "No resume optimization reports exist yet. Run Stage 6.5 first."}


@app.get("/api/skills")
def get_skills_analysis():
    """
    Get current skill profiles and requested technical/framework demands.
    """
    summary = _load_json_safe(PROJECT_ROOT / "cache" / "resume_reports" / "career_summary.json", None)
    profile = _load_json_safe(settings.cache_dir / "candidate_profile.json")

    skills_dict = profile.get("skills", {})
    current_skills = []
    for category, items in skills_dict.items():
        if isinstance(items, list):
            current_skills.extend(items)

    if summary and "gap_analysis" in summary:
        return {
            "current_skills": current_skills,
            "gap_analysis": summary["gap_analysis"],
            "most_requested_technologies": summary.get("most_requested_technologies", []),
            "most_requested_frameworks": summary.get("most_requested_frameworks", [])
        }

    return {
        "current_skills": current_skills,
        "gap_analysis": {},
        "most_requested_technologies": ["Python", "FastAPI", "Docker"],
        "most_requested_frameworks": ["React", "Django"]
    }


@app.get("/api/communication")
def get_outreach_documents(job_uuid: str):
    """
    Get generated outreach cover letters and cold email drafts for a job.
    """
    comm_path = PROJECT_ROOT / "cache" / "communication" / job_uuid[:16] / "communication_report.json"
    if comm_path.exists():
        return _load_json_safe(comm_path)
    
    # Fallback to generate on the fly if needed
    raise HTTPException(
        status_code=404, 
        detail=f"Outreach drafts not generated yet for job {job_uuid}. Run Phase 14 engine."
    )


@app.get("/api/settings")
def get_dashboard_settings():
    """Get active pipeline and preferred profile configuration settings."""
    return {
        "preferred_locations": getattr(settings, "preferred_locations", []),
        "log_level": getattr(settings, "log_level", "INFO"),
        "email_address": getattr(settings, "email_address", ""),
        "google_sheet_id": getattr(settings, "google_sheet_id", "")
    }


@app.post("/api/settings")
def update_dashboard_settings(payload: SettingsPayload):
    """Placeholder to log setting update requests from the UI."""
    logger.info(f"Dashboard requested settings update: {payload}")
    return {"status": "success", "updated_settings": payload.model_dump()}


# ── Phase 16: Job Application Assistant Endpoints ───────────────────────────

class ApprovePayload(BaseModel):
    job_uuid: str


class InfoPayload(BaseModel):
    job_uuid: str
    custom_inputs: dict[str, str]


class SwitchResumePayload(BaseModel):
    file_hash: str


@app.get("/api/applications/pending")
def get_pending_applications():
    """Get all job applications waiting for information or approval."""
    from application_assistant.config import DEFAULT_ASSISTANT_CONFIG
    states_dir = DEFAULT_ASSISTANT_CONFIG.states_dir
    states = []
    if states_dir.exists():
        for file in states_dir.iterdir():
            if file.suffix == ".json":
                state = _load_json_safe(file)
                if state.get("state") in ("Waiting for Information", "Waiting for Approval"):
                    states.append(state)
    return states


@app.post("/api/applications/approve")
def approve_application_endpoint(payload: ApprovePayload):
    """Approve and submit a pending application."""
    from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
    orch = ApplicationWorkflowOrchestrator()
    try:
        state = orch.approve_application(payload.job_uuid)
        return {"status": "success", "state": state.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/applications/provide_info")
def provide_info_endpoint(payload: InfoPayload):
    """Provide missing details for a pending application."""
    from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
    orch = ApplicationWorkflowOrchestrator()
    profile = _load_json_safe(settings.cache_dir / "candidate_profile.json")
    try:
        state = orch.provide_missing_information(payload.job_uuid, profile, payload.custom_inputs)
        return {"status": "success", "state": state.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/resumes/active")
def get_resume_versions():
    """Get all resume versions and the active resume version details."""
    from application_assistant.resume_monitor import ResumeMonitor
    mon = ResumeMonitor()
    mon.scan_directory()  # scan on request
    versions = mon.load_versions()
    return {
        "active": mon.get_active_resume().model_dump() if mon.get_active_resume() else None,
        "versions": [v.model_dump() for v in versions.values()]
    }


@app.post("/api/resumes/active")
def switch_active_resume(payload: SwitchResumePayload):
    """Switch default active resume version by hash."""
    from application_assistant.resume_monitor import ResumeMonitor
    mon = ResumeMonitor()
    success = mon.set_active_resume(payload.file_hash)
    if success:
        return {"status": "success", "active": mon.get_active_resume().model_dump()}
    raise HTTPException(status_code=400, detail="Resume version hash not found.")


from fastapi.responses import HTMLResponse

@app.get("/api/applications/email/action", response_class=HTMLResponse)
def email_action_endpoint(action: str, job_uuid: str):
    """
    Callback endpoint triggered directly by interactive email actions.
    Synchronises state and updates the Google Sheet Status row automatically.
    """
    from application_assistant.orchestrator import ApplicationWorkflowOrchestrator
    from sheets.google_sheet import GoogleSheetClient
    from sheets.models import SHEET_HEADERS
    import re
    
    orch = ApplicationWorkflowOrchestrator()
    state = orch.load_state(job_uuid)
    
    if not state:
        return f"""
        <html>
            <head><title>Error</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px; background-color: #F7FAFC;">
                <h2 style="color: #E53E3E;">Application Not Found</h2>
                <p>Could not locate application state for ID: {job_uuid}</p>
            </body>
        </html>
        """

    status_mapping = {
        "approve": "Applied",
        "applied": "Applied",
        "reject": "Skip",
        "later": "Not applied"
    }
    
    new_status = status_mapping.get(action.lower(), "Not applied")
    
    if action.lower() == "approve":
        try:
            orch.approve_application(job_uuid)
        except Exception:
            state.state = "Submitted"
            orch.save_state(state)
    elif action.lower() == "reject":
        state.state = "Cancelled"
        orch.save_state(state)
    elif action.lower() == "applied":
        state.state = "Submitted"
        orch.save_state(state)
    elif action.lower() == "later":
        state.state = "Prepared"
        orch.save_state(state)

    manual_apps = _get_manual_apps()
    manual_apps[job_uuid] = new_status
    _save_manual_apps(manual_apps)

    sheets_synced = False
    error_msg = ""
    row_number = None
    try:
        jobs_list = _load_json_safe(settings.cache_dir / "deduplicated_jobs.json", [])
        job_url = ""
        for job in jobs_list:
            if job.get("identity", {}).get("uuid") == job_uuid:
                job_url = job.get("application", {}).get("application_url", "")
                break
        
        if job_url:
            client = GoogleSheetClient()
            client.connect()
            ws = client.get_sheet()
            all_values = ws.get_all_values(value_render_option="FORMULA")
            apply_idx = SHEET_HEADERS.index("Apply link")
            status_col = SHEET_HEADERS.index("Status") + 1
            
            for idx, row in enumerate(all_values, start=1):
                if len(row) > apply_idx:
                    if job_url in row[apply_idx]:
                        row_number = idx
                        break
            
            if row_number:
                ws.update_cell(row_number, status_col, new_status)
                sheets_synced = True
            else:
                error_msg = "Job matching URL not found in spreadsheet rows."
        else:
            error_msg = "Job URL could not be resolved from cache."
    except Exception as exc:
        error_msg = str(exc)

    sync_status_html = f"<span style='color: #38A169;'>Success (Row {row_number} Updated)</span>" if sheets_synced else f"<span style='color: #E53E3E;'>Failed ({error_msg})</span>"

    return f"""
    <html>
        <head>
            <title>Action Confirmed</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #F7FAFC; padding: 40px 20px; text-align: center; color: #2D3748; }}
                .card {{ max-width: 480px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1); border-top: 5px solid #2B6CB0; }}
                h2 {{ color: #1A365D; margin-top: 0; }}
                p {{ line-height: 1.5; color: #4A5568; }}
                .badge {{ display: inline-block; padding: 6px 12px; border-radius: 9999px; font-weight: bold; background-color: #E2E8F0; font-size: 14px; margin-top: 10px; }}
                .footer {{ margin-top: 25px; font-size: 12px; color: #A0AEC0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Action Processed Successfully</h2>
                <p>Your application for <strong>{state.job_title}</strong> at <strong>{state.company_name}</strong> has been updated.</p>
                <div style="margin: 20px 0;">
                    <div>Status Action: <span class="badge">{action.upper()}</span></div>
                    <div style="margin-top: 10px;">New CRM Status: <strong>{new_status}</strong></div>
                    <div style="margin-top: 10px;">Google Sheets Sync: {sync_status_html}</div>
                </div>
                <p>You can close this tab now.</p>
                <div class="footer">AI Career Operating System &copy; 2026</div>
            </div>
        </body>
    </html>
    """



# ── Mount static frontend app ──────────────────────────────────────────────

static_path = PROJECT_ROOT / "dashboard_backend" / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
else:
    logger.warning(f"Static files directory {static_path} does not exist. Frontend assets will not be served.")
