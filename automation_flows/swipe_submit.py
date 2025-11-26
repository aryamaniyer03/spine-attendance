"""Flow wrapper around swipe submissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from swipe_manager import submit_swipe_request
from automation_shared import should_use_headless


@dataclass
class SwipeSubmissionAutomation:
    swipe_date: date
    reason: str
    swipe_type: str = "both"
    headless: bool | None = None

    def run(self) -> dict:
        result = submit_swipe_request(
            self.swipe_date,
            self.reason,
            swipe_type=self.swipe_type,
            headless=should_use_headless(self.headless),
        )

        return {
            "success": result.get("success", False),
            "message": result.get("message", "Swipe submission completed."),
            "details": result,
        }
