# Intelligent Email Notification & AI Career Report Engine

## Overview
Phase 10 of the AI-Job-Tracker introduces an advanced notification engine. Rather than simply alerting the user of each job discovery, it aggregates the data into a professional HTML career report and sends it daily after the job pipeline completes.

## Architecture
The notification system is modular, using an abstract base class `Notifier` to allow for seamless integration of alternative notification channels in the future (e.g., Slack, SMS).

- **`Notifier` (base.py)**: The contract enforcing the `send_report` implementation.
- **`EmailNotifier` (email_notifier.py)**: Adapts the `Notifier` interface to send responsive HTML emails using Python's native `smtplib`. It authenticates using Gmail SMTP credentials defined in `config.py`.
- **`ReportGenerator` (report_generator.py)**: Responsible for executing business logic to extract insights (top matches, skills gap analysis, PPO-eligible internships) and rendering the data into HTML using `Jinja2`.

## Execution Criteria
To prevent spam, the notification engine skips sending an email if:
- No jobs were discovered during the pipeline run.
- The only jobs discovered were duplicates or have already expired.

## HTML Templates
The engine uses Jinja2 to render `notifications/templates/career_report.html`, creating a visually appealing and actionable experience directly inside the user's inbox.
