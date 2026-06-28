"""
Conservative safety monitoring for possible exit-risk situations.

The monitor records "possible" safety events with reasons and confidence. It
does not make medical or emergency claims; caregivers remain in the loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from memory.patient_profile import PatientProfile, get_patient_profile


SAFETY_EVENTS_PATH = os.path.join("memory", "safety_events.jsonl")


@dataclass
class SafetyEvent:
    id: str
    event_type: str
    confidence: str
    reason: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    facts: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SafetyMonitor:
    EXIT_OBJECTS = {"house_keys", "keys", "wallet", "coat", "purse"}

    def __init__(self, events_path: str = SAFETY_EVENTS_PATH, profile: Optional[PatientProfile] = None):
        self.events_path = events_path
        self.profile = profile or get_patient_profile()
        os.makedirs(os.path.dirname(self.events_path), exist_ok=True)

    def evaluate_context(
        self,
        detected_objects: Optional[List[str]] = None,
        room: Optional[str] = None,
        near_exit: bool = False,
        now: Optional[datetime] = None,
    ) -> Optional[SafetyEvent]:
        if not self.profile.exit_risk_enabled:
            return None

        detected = {obj.lower() for obj in (detected_objects or [])}
        exit_objects_seen = sorted(detected.intersection(self.EXIT_OBJECTS))
        in_risk_time = self._is_high_risk_time(now or datetime.now())

        if not near_exit and not exit_objects_seen:
            return None

        confidence = "low"
        reasons = []
        if near_exit:
            reasons.append("person or object is near configured exit area")
            confidence = "medium"
        if exit_objects_seen:
            reasons.append(f"exit-related object seen: {', '.join(exit_objects_seen)}")
            confidence = "medium"
        if in_risk_time and (near_exit or exit_objects_seen):
            reasons.append("event happened during configured high-risk time")
            confidence = "high" if near_exit and exit_objects_seen else "medium"

        event = SafetyEvent(
            id=str(uuid.uuid4()),
            event_type="possible_exit_risk",
            confidence=confidence,
            reason="; ".join(reasons),
            action="calm_redirect_prompt",
            facts={
                "detected_objects": sorted(detected),
                "room": room,
                "near_exit": near_exit,
                "high_risk_time": in_risk_time,
            },
        )
        self.log_event(event)
        return event

    def log_event(self, event: SafetyEvent):
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def list_events(self, limit: int = 50) -> List[SafetyEvent]:
        if not os.path.exists(self.events_path):
            return []
        events = []
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(SafetyEvent(**json.loads(line)))
                except Exception:
                    continue
        return events[-limit:]

    def acknowledge(self, event_id: str) -> bool:
        events = self.list_events(limit=10000)
        changed = False
        for event in events:
            if event.id == event_id:
                event.acknowledged = True
                event.acknowledged_at = datetime.now().isoformat()
                changed = True
        if changed:
            with open(self.events_path, "w", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event.to_dict()) + "\n")
        return changed

    def _is_high_risk_time(self, now: datetime) -> bool:
        for window in self.profile.high_risk_times:
            try:
                start = self._parse_time(window["start"])
                end = self._parse_time(window["end"])
            except Exception:
                continue
            current = now.time()
            if start <= end:
                if start <= current <= end:
                    return True
            elif current >= start or current <= end:
                return True
        return False

    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = [int(part) for part in value.split(":", 1)]
        return time(hour=hour, minute=minute)
