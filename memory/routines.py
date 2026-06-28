"""
memory/routines.py — Morning reorientation, medication reminders, rotating memory tips.
"""

import datetime
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

SETTINGS_FILE = os.path.join("data", "memory", "routines.json")
ADVANCED_ROUTINES_FILE = os.path.join("memory", "advanced_routines.json")


def _load_routines() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "morning_enabled": True,
        "morning_hour": 8,
        "rotating_tips": [],
        "last_morning_date": "",
        "last_tip_index": 0,
    }


def _save_routines(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_morning_greeting(user_name: str) -> str:
    now = datetime.datetime.now()
    day = now.strftime("%A, %B %d, %Y")
    hour = now.hour
    if hour < 12:
        salutation = "Good morning"
    elif hour < 17:
        salutation = "Good afternoon"
    else:
        salutation = "Good evening"
    return f"{salutation}, {user_name}. Today is {day}."


def check_morning_prompt(user_name: str) -> Optional[str]:
    """Return greeting if we haven't shown morning prompt today."""
    data = _load_routines()
    if not data.get("morning_enabled", True):
        return None
    today = datetime.date.today().isoformat()
    if data.get("last_morning_date") == today:
        return None
    hour = datetime.datetime.now().hour
    if hour < data.get("morning_hour", 8):
        return None
    data["last_morning_date"] = today
    _save_routines(data)
    return get_morning_greeting(user_name)


def get_rotating_tip(vault_objects: List[Any]) -> Optional[str]:
    """Pick a gentle memory tip from saved objects."""
    data = _load_routines()
    tips = data.get("rotating_tips") or []
    if vault_objects:
        for obj in vault_objects[:5]:
            name = obj.name if hasattr(obj, "name") else obj.get("name", "Unknown")
            tips.append(f"Remember: {name} is in your memory vault.")
    if not tips:
        return None
    idx = data.get("last_tip_index", 0) % len(tips)
    data["last_tip_index"] = idx + 1
    _save_routines(data)
    return tips[idx]


def format_medication_reminder(med: dict) -> str:
    note = med.get("note") or ""
    base = f"Medication reminder: {med['name']}."
    if note:
        return f"{base} {note}"
    return base


def check_medication_reminders(vault, spoken_today: set) -> Optional[Tuple[str, int]]:
    """Return (message, object_id) for due meds not yet spoken today."""
    due = vault.medications_due_now()
    today = datetime.date.today().isoformat()
    for med in due:
        key = f"{today}:{med['id']}"
        if key in spoken_today:
            continue
        return format_medication_reminder(med), med["id"]
    return None


@dataclass
class RoutineStep:
    id: str
    title: str
    time_window: str = ""
    expected_objects: List[str] = field(default_factory=list)
    prompt: str = ""
    follow_up_prompt: str = ""
    confirmation_type: str = "user"
    priority: int = 3
    caregiver_alert_after_minutes: int = 0
    completed_at: Optional[str] = None
    skipped_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutinePlan:
    id: str
    name: str
    enabled: bool = True
    steps: List[RoutineStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutinePlan":
        payload = dict(data)
        payload["steps"] = [RoutineStep(**step) for step in payload.get("steps", [])]
        return cls(**payload)


class AdvancedRoutineStore:
    """Editable caregiver routines shared by dashboard and MEMO mode."""

    def __init__(self, path: str = ADVANCED_ROUTINES_FILE):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        if os.path.exists(self.path):
            return
        defaults = [
            RoutinePlan(
                id="morning",
                name="Morning Routine",
                steps=[
                    RoutineStep(
                        id="glasses",
                        title="Put on glasses",
                        time_window="08:00-09:30",
                        expected_objects=["reading_glasses"],
                        prompt="Let's find your glasses. They are usually in their safe place.",
                        follow_up_prompt="Can you show the glasses to the camera?",
                        priority=4,
                    ),
                    RoutineStep(
                        id="water",
                        title="Drink water",
                        time_window="08:00-10:00",
                        expected_objects=["water_glass"],
                        prompt="A drink of water can help start the morning.",
                    ),
                ],
            ),
            RoutinePlan(
                id="medication",
                name="Medication Support",
                steps=[
                    RoutineStep(
                        id="pill_bottle",
                        title="Find pill bottle",
                        time_window="12:00-13:00",
                        expected_objects=["pill_bottle"],
                        prompt="It's time to check your medication. Let's find the pill bottle.",
                        follow_up_prompt="Please wait for a caregiver if you are unsure.",
                        priority=5,
                        caregiver_alert_after_minutes=15,
                    )
                ],
            ),
        ]
        self.save_all(defaults)

    def load_all(self) -> List[RoutinePlan]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [RoutinePlan.from_dict(item) for item in data.get("routines", [])]
        except Exception:
            return []

    def save_all(self, routines: List[RoutinePlan]):
        for routine in routines:
            routine.updated_at = datetime.datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"routines": [routine.to_dict() for routine in routines]}, f, indent=2)

    def get(self, routine_id: str) -> Optional[RoutinePlan]:
        for routine in self.load_all():
            if routine.id == routine_id:
                return routine
        return None

    def upsert(self, payload: Dict[str, Any]) -> RoutinePlan:
        routine_id = payload.get("id") or str(uuid.uuid4())
        steps = [
            RoutineStep(
                id=step.get("id") or str(uuid.uuid4()),
                title=step["title"],
                time_window=step.get("time_window", ""),
                expected_objects=step.get("expected_objects", []),
                prompt=step.get("prompt", step["title"]),
                follow_up_prompt=step.get("follow_up_prompt", ""),
                confirmation_type=step.get("confirmation_type", "user"),
                priority=int(step.get("priority", 3)),
                caregiver_alert_after_minutes=int(step.get("caregiver_alert_after_minutes", 0)),
                completed_at=step.get("completed_at"),
                skipped_at=step.get("skipped_at"),
            )
            for step in payload.get("steps", [])
        ]
        routine = RoutinePlan(
            id=routine_id,
            name=payload.get("name", "Routine"),
            enabled=bool(payload.get("enabled", True)),
            steps=steps,
            created_at=payload.get("created_at", datetime.datetime.now().isoformat()),
        )

        routines = self.load_all()
        for idx, existing in enumerate(routines):
            if existing.id == routine.id:
                routines[idx] = routine
                self.save_all(routines)
                return routine
        routines.append(routine)
        self.save_all(routines)
        return routine

    def due_steps(self, now: Optional[datetime.datetime] = None) -> List[Tuple[RoutinePlan, RoutineStep]]:
        now = now or datetime.datetime.now()
        due = []
        for routine in self.load_all():
            if not routine.enabled:
                continue
            for step in routine.steps:
                if step.completed_at or step.skipped_at:
                    continue
                if self._in_window(step.time_window, now):
                    due.append((routine, step))
        due.sort(key=lambda item: item[1].priority, reverse=True)
        return due

    @staticmethod
    def _in_window(window: str, now: datetime.datetime) -> bool:
        if not window or "-" not in window:
            return True
        try:
            start_value, end_value = window.split("-", 1)
            start = datetime.datetime.strptime(start_value.strip(), "%H:%M").time()
            end = datetime.datetime.strptime(end_value.strip(), "%H:%M").time()
        except ValueError:
            return True
        current = now.time()
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end
