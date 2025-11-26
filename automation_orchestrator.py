"""Central orchestrator to invoke individual Selenium automation flows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from automation_flows.clock_in import ClockInAutomation
from automation_flows.clock_out import ClockOutAutomation
from automation_flows.swipe_submit import SwipeSubmissionAutomation
from automation_flows.attendance_check import AttendanceCheckAutomation
from automation_flows.swipe_status import SwipeStatusAutomation


class AutomationOrchestrator:
    """Facade that exposes the supported automation flows."""

    def clock_in(self, headless: Optional[bool] = None) -> dict:
        return ClockInAutomation(headless=headless).run()

    def clock_out(self, headless: Optional[bool] = None) -> dict:
        return ClockOutAutomation(headless=headless).run()

    def submit_swipe(
        self,
        swipe_date: date,
        reason: str,
        swipe_type: str = "both",
        headless: Optional[bool] = None,
    ) -> dict:
        return SwipeSubmissionAutomation(
            swipe_date=swipe_date,
            reason=reason,
            swipe_type=swipe_type,
            headless=headless,
        ).run()

    def check_attendance(self, headless: Optional[bool] = None) -> dict:
        return AttendanceCheckAutomation(headless=headless).run()

    def check_swipe_status(self, limit: int = 20, headless: Optional[bool] = None) -> dict:
        return SwipeStatusAutomation(limit=limit, headless=headless).run()


__all__ = ["AutomationOrchestrator"]

