from __future__ import annotations

from unittest.mock import Mock

from sheets.career_tracker import CareerTracker


def test_init_analytics_dashboard_layout_uses_simple_summary_formulas() -> None:
    tracker = CareerTracker(sheet_title="Tracker")
    tracker.analytics_sheet = Mock()
    tracker.analytics_sheet.id = 123
    tracker.analytics_sheet.clear = Mock()
    tracker.analytics_sheet.update = Mock()

    tracker.init_analytics_dashboard_layout()

    first_update_call = tracker.analytics_sheet.update.call_args_list[0]
    values = first_update_call.kwargs["values"]
    flattened = [cell for row in values for cell in row if isinstance(cell, str)]

    # Banner title
    assert any("ANALYTICS DASHBOARD" in c for c in flattened)
    # KPI labels
    assert "Total Jobs" in flattened
    assert "Applied" in flattened
    # Section headers
    assert "APPLICATION STATUS BREAKDOWN" in flattened
    assert "MATCH SCORE DISTRIBUTION" in flattened
    # Formulas use COUNTIFS with exclusion filter
    assert any("COUNTIFS" in c for c in flattened)
    assert any("pytest-seed-test" in c for c in flattened)
