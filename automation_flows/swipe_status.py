"""Flow wrapper that fetches recent swipe application statuses."""

from __future__ import annotations

from dataclasses import dataclass

from swipe_manager import get_recent_swipe_applications
from automation_shared import should_use_headless


@dataclass
class SwipeStatusAutomation:
    limit: int = 20
    headless: bool | None = None

    def run(self) -> dict:
        entries = get_recent_swipe_applications(limit=self.limit, headless=should_use_headless(self.headless))
        return {
            "success": True,
            "message": f"Retrieved {len(entries)} swipe application(s).",
            "details": entries,
        }
