"""
scripts/backup_manager.py — Automated Backup Manager
=====================================================
Purpose
-------
Creates a timestamped, compressed archive of the pipeline's current output
(cache/, logs/, health reports). Old backups beyond the retention policy
are automatically pruned to keep the disk clean.

Usage
-----
    python scripts/backup_manager.py              # create today's backup
    python scripts/backup_manager.py --prune-only # only delete old backups
    python scripts/backup_manager.py --list       # list existing backups

Design
------
Each run creates:
    backups/YYYY-MM-DD_HH-MM-SS/
        ├── cache/        (all JSON outputs)
        ├── logs/         (all log files)
        └── health_report.json

The `backup_retention_days` setting in config.py (default: 7) controls
how many days' worth of backups are kept.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import settings
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)

# Files that must NEVER be deleted (user data)
PROTECTED_PATTERNS: list[str] = [
    "candidate_profile.json",
    "resume_hash.txt",
    "google_credentials.json",
    ".env",
]

# Directories to back up
BACKUP_SOURCES: list[tuple[str, Path]] = [
    ("cache", settings.cache_dir),
    ("logs", settings.log_dir),
]


def create_backup() -> Path:
    """
    Create a timestamped backup of the current pipeline outputs.

    Returns
    -------
    Path
        The path to the newly-created backup directory.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = settings.backup_dir / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)

    logger.info("Creating backup at: %s", backup_path)
    copied_count = 0

    for folder_name, source_dir in BACKUP_SOURCES:
        if not source_dir.exists():
            logger.debug("Source directory does not exist, skipping: %s", source_dir)
            continue

        dest_dir = backup_path / folder_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file in source_dir.glob("*"):
            if file.is_file():
                try:
                    shutil.copy2(file, dest_dir / file.name)
                    copied_count += 1
                    logger.debug("Backed up: %s", file.name)
                except Exception as exc:
                    logger.warning("Failed to back up %s: %s", file, exc)

    # Write a backup manifest
    manifest = {
        "created_at": datetime.now().isoformat(),
        "source_files_copied": copied_count,
        "sources": [str(s) for _, s in BACKUP_SOURCES],
    }
    (backup_path / "backup_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    logger.info("Backup complete: %d files copied to %s", copied_count, backup_path)
    return backup_path


def prune_old_backups(retention_days: int | None = None) -> int:
    """
    Delete backup directories older than the retention period.

    Parameters
    ----------
    retention_days : int, optional
        Days to retain. Defaults to settings.backup_retention_days.

    Returns
    -------
    int
        Number of backup directories pruned.
    """
    days = retention_days if retention_days is not None else settings.backup_retention_days
    cutoff = datetime.now() - timedelta(days=days)
    backup_dir = settings.backup_dir
    pruned = 0

    if not backup_dir.exists():
        return 0

    for entry in sorted(backup_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            folder_dt = datetime.strptime(entry.name, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            continue  # Not a timestamped backup folder, skip

        if folder_dt < cutoff:
            try:
                shutil.rmtree(entry)
                pruned += 1
                logger.info("Pruned old backup: %s", entry.name)
            except Exception as exc:
                logger.warning("Failed to prune backup %s: %s", entry, exc)

    if pruned:
        logger.info("Pruned %d old backups (retention: %d days).", pruned, days)
    else:
        logger.info("No old backups to prune (retention: %d days).", days)

    return pruned


def list_backups() -> list[Path]:
    """Return a list of existing backup directories sorted by date."""
    backup_dir = settings.backup_dir
    if not backup_dir.exists():
        return []
    return sorted(
        [d for d in backup_dir.iterdir() if d.is_dir()],
        reverse=True
    )


def run(prune_only: bool = False, list_only: bool = False) -> None:
    """Main entry point for the backup manager CLI."""
    DIVIDER = "=" * 60
    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Backup Manager")
    print(DIVIDER)

    if list_only:
        backups = list_backups()
        if backups:
            print(f"\n[+]  Found {len(backups)} backup(s):")
            for b in backups:
                manifest_file = b / "backup_manifest.json"
                size_mb = sum(f.stat().st_size for f in b.rglob("*") if f.is_file()) / (1024 * 1024)
                print(f"      - {b.name}  ({size_mb:.1f} MB)")
        else:
            print("\n[INFO]  No backups found.")
        return

    if not prune_only:
        backup_path = create_backup()
        print(f"\n[OK]  Backup created at: {backup_path}")

    pruned = prune_old_backups()
    print(f"[OK]  Pruned {pruned} old backup(s) (retention: {settings.backup_retention_days} days).")

    print(f"\n{DIVIDER}")
    print("[OK]  Backup Manager complete.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Job Tracker Backup Manager")
    parser.add_argument("--prune-only", action="store_true", help="Only delete old backups, skip creating a new one.")
    parser.add_argument("--list", action="store_true", dest="list_only", help="List all existing backups.")
    args = parser.parse_args()
    run(prune_only=args.prune_only, list_only=args.list_only)
