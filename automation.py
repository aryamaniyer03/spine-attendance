"""High-level orchestration facade for Spine automation flows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from automation_orchestrator import AutomationOrchestrator
from automation_shared import (
    URL,
    USERNAME,
    PASSWORD,
    should_use_headless,
    setup_driver,
    login,
    go_to_attendance,
    go_to_swipe_form,
    go_to_recent_swipe_applications,
)

_orchestrator = AutomationOrchestrator()


def clock_in(headless: Optional[bool] = None) -> dict:
    """Run the dedicated clock-in automation flow."""

    return _orchestrator.clock_in(headless=headless)


def clock_out(headless: Optional[bool] = None) -> dict:
    """Run the dedicated clock-out automation flow."""

    return _orchestrator.clock_out(headless=headless)


def submit_swipe(
    swipe_date: date,
    reason: str,
    swipe_type: str = "both",
    headless: Optional[bool] = None,
) -> dict:
    """Submit a swipe request via Selenium automation."""

    return _orchestrator.submit_swipe(
        swipe_date=swipe_date,
        reason=reason,
        swipe_type=swipe_type,
        headless=headless,
    )


def check_attendance(headless: Optional[bool] = None) -> dict:
    """Retrieve today's attendance status using automation."""

    return _orchestrator.check_attendance(headless=headless)


def check_swipe_status(limit: int = 20, headless: Optional[bool] = None) -> dict:
    """Fetch the recent swipe application statuses."""

    return _orchestrator.check_swipe_status(limit=limit, headless=headless)


def run_automation_process(action: str, headless: Optional[bool] = None) -> str:
    """Backward-compatible wrapper for legacy scripts.

    Returns a human-readable string describing the outcome, preserving the
    behaviour expected by existing CLI utilities.
    """

    action = action.lower()

    if action == "clock_in":
        result = clock_in(headless=headless)
    elif action == "clock_out":
        result = clock_out(headless=headless)
    else:
        return f"Error: Unknown action '{action}'."

    return result.get("message", "Process completed.")


__all__ = [
    "URL",
    "USERNAME",
    "PASSWORD",
    "should_use_headless",
    "setup_driver",
    "login",
    "go_to_attendance",
    "go_to_swipe_form",
    "go_to_recent_swipe_applications",
    "AutomationOrchestrator",
    "clock_in",
    "clock_out",
    "submit_swipe",
    "check_attendance",
    "check_swipe_status",
    "run_automation_process",
]
