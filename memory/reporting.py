"""
Caregiver reports with fact/interpretation separation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from typing import Any, Dict, List

from memory.safety_monitor import SafetyMonitor
from memory.task_guidance import TASK_LOG_PATH


ACTIVITY_LOG_PATH = os.path.join("memory", "activity_log.jsonl")


class CaregiverReport:
    def __init__(
        self,
        activity_path: str = ACTIVITY_LOG_PATH,
        task_log_path: str = TASK_LOG_PATH,
        safety_monitor: SafetyMonitor | None = None,
    ):
        self.activity_path = activity_path
        self.task_log_path = task_log_path
        self.safety_monitor = safety_monitor or SafetyMonitor()

    def build_daily_report(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = datetime.now() - timedelta(hours=hours)
        activities = self._read_jsonl_since(self.activity_path, cutoff)
        task_events = self._read_jsonl_since(self.task_log_path, cutoff)
        safety_events = [
            event.to_dict()
            for event in self.safety_monitor.list_events(limit=200)
            if datetime.fromisoformat(event.timestamp) >= cutoff
        ]

        return {
            "generated_at": datetime.now().isoformat(),
            "window_hours": hours,
            "facts": {
                "activity_events": activities,
                "task_events": task_events,
                "safety_events": safety_events,
            },
            "uncertainty_note": (
                "Camera and user-interface events are observations, not medical "
                "confirmation. Medication completion should be verified by a "
                "caregiver when needed."
            ),
            "summary": {
                "activity_count": len(activities),
                "task_event_count": len(task_events),
                "safety_event_count": len(safety_events),
                "unacknowledged_safety_count": len(
                    [event for event in safety_events if not event.get("acknowledged")]
                ),
            },
        }

    def export_daily_report(self, filepath: str = os.path.join("memory", "caregiver_report.json")) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.build_daily_report(), f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def _read_jsonl_since(path: str, cutoff: datetime) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                except Exception:
                    continue
                if timestamp >= cutoff:
                    entries.append(entry)
        return entries
