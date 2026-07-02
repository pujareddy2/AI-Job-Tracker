"""
scripts/resume_optimizer_cli.py — CLI for the Resume Optimization Engine
=========================================================================
Purpose
-------
Manually trigger the Resume Optimization Engine without running the full
pipeline. Useful for ad-hoc analysis after the pipeline has already run.

Usage
-----
    python scripts/resume_optimizer_cli.py
    python scripts/resume_optimizer_cli.py --top 5
    python scripts/resume_optimizer_cli.py --summary-only
    python scripts/resume_optimizer_cli.py --job-id <uuid>

Output
------
    cache/resume_reports/<uuid>_report.json  — per-job reports
    cache/resume_reports/career_summary.json — career summary
    cache/resume_reports/latest_reports.json — index

Requires
--------
    - cache/candidate_profile.json (from pipeline Stage 2)
    - cache/deduplicated_jobs.json  (from pipeline Stage 7)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from resume_optimizer.engine import ResumeOptimizationEngine
from resume_optimizer.config import OptimizerConfig
from utils.logger import get_logger

logger = get_logger("resume_optimizer_cli")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Resume Optimization & ATS Analysis Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/resume_optimizer_cli.py
  python scripts/resume_optimizer_cli.py --top 10
  python scripts/resume_optimizer_cli.py --summary-only
  python scripts/resume_optimizer_cli.py --job-id abc123
        """,
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top-matched jobs to analyze (default: 20).",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print the career summary (faster — skips per-job detail).",
    )
    parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Analyze only the job with this UUID prefix.",
    )
    parser.add_argument(
        "--jobs-file",
        type=str,
        default=None,
        help="Path to a custom jobs JSON file (default: cache/deduplicated_jobs.json).",
    )
    return parser.parse_args()


def load_jobs(jobs_file: str | None, top_n: int) -> list[dict]:
    """Load and sort jobs from the deduplicated jobs cache."""
    if jobs_file:
        path = Path(jobs_file)
    else:
        path = settings.cache_dir / "deduplicated_jobs.json"

    if not path.exists():
        logger.error(f"Jobs file not found: {path}")
        print(f"\n❌ Jobs file not found: {path}")
        print("Run the full pipeline first: python main.py")
        sys.exit(1)

    raw = json.loads(path.read_text(encoding="utf-8"))
    # Sort by match score descending
    raw.sort(
        key=lambda j: j.get("resume_match", {}).get("candidate_match_score") or 0,
        reverse=True,
    )
    return raw[:top_n]


def print_report_summary(report) -> None:
    """Print a concise per-job report summary to stdout."""
    sc = report.ats_scorecard
    imp = report.improvement_scorecard
    print(f"\n{'='*70}")
    print(f"  📋 {report.job_title} @ {report.company_name}")
    print(f"  🎯 ATS Score: {sc.overall_ats_score:.1f}/100  ({sc.fit_category})")
    print(f"  📈 Estimated after improvements: {imp.optimized_ats_score:.1f}/100 (+{imp.expected_ats_improvement:.1f})")
    print(f"  📊 Keyword coverage: {report.keyword_analysis.keyword_coverage_pct:.1f}%")
    print(f"  💡 Top suggestions:")
    for sug in report.top_suggestions(3):
        print(f"     [{sug.priority}] {sug.action}")
    if report.keyword_analysis.missing_keywords:
        print(f"  🔑 Top missing keywords: {', '.join(report.keyword_analysis.missing_keywords[:5])}")


def print_career_summary(summary) -> None:
    """Print the career summary to stdout."""
    print(f"\n{'='*70}")
    print(f"  🧠 CAREER SUMMARY — {summary.candidate_name}")
    print(f"  📅 {summary.generated_at[:10]}")
    print(f"  📊 Jobs analyzed: {summary.total_jobs_analyzed}")
    print(f"  🎯 Average ATS score: {summary.average_ats_score:.1f}/100")
    print()
    print("  🏆 Best fit jobs:")
    for job in summary.best_fit_jobs:
        print(f"     • {job}")
    print()
    if summary.gap_analysis.top_missing_skills:
        print("  ⚠️  Top skill gaps:")
        for gap in summary.gap_analysis.top_missing_skills[:5]:
            print(f"     [{gap.priority}] {gap.name} ({gap.frequency_pct:.0f}% of jobs)")
    print()
    if summary.gap_analysis.learning_path:
        print("  📚 Recommended learning path:")
        for step in summary.gap_analysis.learning_path[:4]:
            print(f"     {step.order}. {step.action} (~{step.estimated_weeks} weeks) [{step.priority}]")
    print()
    if summary.career_growth_suggestions:
        print("  🚀 Career growth suggestions:")
        for sug in summary.career_growth_suggestions[:3]:
            print(f"     • {sug}")
    print(f"{'='*70}\n")


def main() -> None:
    args = parse_args()

    print("\n🤖 AI Resume Optimization & ATS Analysis Engine")
    print("================================================\n")

    # Initialize engine
    config = OptimizerConfig(top_n_jobs=args.top)
    engine = ResumeOptimizationEngine(config)

    # Load profile
    try:
        profile = engine.load_profile()
        name = profile.get("personal", {}).get("name", "Candidate")
        print(f"✅ Profile loaded: {name}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Load jobs
    jobs = load_jobs(args.jobs_file, args.top)
    if not jobs:
        print("❌ No jobs found. Run the full pipeline first.")
        sys.exit(1)

    # Filter by job-id if specified
    if args.job_id:
        jobs = [j for j in jobs if j.get("identity", {}).get("uuid", "").startswith(args.job_id)]
        if not jobs:
            print(f"❌ No job found with ID prefix: {args.job_id}")
            sys.exit(1)

    print(f"📂 Analyzing top {len(jobs)} jobs…\n")

    # Run analysis
    reports = engine.analyze_all_jobs(profile, jobs)

    if not args.summary_only:
        for report in reports[:5]:  # Show first 5 in console
            print_report_summary(report)

    # Generate and save
    summary = engine.generate_career_summary(profile, reports)
    output_dir = engine.save_reports(reports, summary)

    print_career_summary(summary)

    print(f"✅ Reports saved to: {output_dir}")
    print(f"   • {len(reports)} per-job reports")
    print(f"   • career_summary.json")
    print(f"   • latest_reports.json")


if __name__ == "__main__":
    main()
