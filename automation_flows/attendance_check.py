"""Flow wrapper around attendance status checks."""

from __future__ import annotations

from dataclasses import dataclass

from attendance_checker import attendance_checker
from automation_shared import should_use_headless


@dataclass
class AttendanceCheckAutomation:
    headless: bool | None = None

    def run(self) -> dict:
        status = attendance_checker.check_todays_attendance(headless=should_use_headless(self.headless))
        success = status is not None and not status.get("error")

        return {
            "success": success,
            "message": "Attendance status retrieved." if success else status.get("error", "Unable to fetch status."),
            "details": status,
        }
