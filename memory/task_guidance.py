"""
Step-by-step task guidance for dementia support.

Tasks are intentionally explicit and uncertainty-aware. Camera detections can
support a step, but completion should come from user or caregiver confirmation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional


TASKS_PATH = os.path.join("memory", "guided_tasks.json")
TASK_LOG_PATH = os.path.join("memory", "task_log.jsonl")


@dataclass
class TaskStep:
    id: str
    instruction: str
    expected_objects: List[str] = field(default_factory=list)
    confirmation_type: str = "user"
    completed_at: Optional[str] = None
    completion_source: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuidedTask:
    id: str
    title: str
    prompt: str
    priority: int = 3
    steps: List[TaskStep] = field(default_factory=list)
    active: bool = False
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuidedTask":
        steps = [TaskStep(**step) for step in data.get("steps", [])]
        payload = dict(data)
        payload["steps"] = steps
        return cls(**payload)

    @property
    def current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        return bool(self.completed_at)


class GuidedTaskStore:
    def __init__(self, path: str = TASKS_PATH, log_path: str = TASK_LOG_PATH):
        self.path = path
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._ensure_seed_tasks()

    def _ensure_seed_tasks(self):
        if os.path.exists(self.path):
            return
        tasks = [
            GuidedTask(
                id="take_medication",
                title="Take Medication",
                prompt="Let's take this one step at a time.",
                priority=5,
                steps=[
                    TaskStep("find_pills", "Find your pill bottle.", ["pill_bottle"]),
                    TaskStep("find_water", "Find a glass of water.", ["water_glass"]),
                    TaskStep("sit_down", "Sit down somewhere comfortable."),
                    TaskStep(
                        "confirm_taken",
                        "When you are ready, mark this step done.",
                        confirmation_type="user_or_caregiver",
                    ),
                ],
            ),
            GuidedTask(
                id="prepare_bed",
                title="Prepare For Bed",
                prompt="Let's get ready for a calm night.",
                priority=3,
                steps=[
                    TaskStep("charge_phone", "Put your phone on the charger.", ["phone_charger"]),
                    TaskStep("find_slippers", "Place your slippers near the bed.", ["bedroom_slippers"]),
                    TaskStep("lights", "Turn down bright lights."),
                ],
            ),
        ]
        self.save_all(tasks)

    def load_all(self) -> List[GuidedTask]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [GuidedTask.from_dict(item) for item in data.get("tasks", [])]
        except Exception:
            return []

    def save_all(self, tasks: List[GuidedTask]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"tasks": [task.to_dict() for task in tasks]}, f, indent=2)

    def get_task(self, task_id: str) -> Optional[GuidedTask]:
        for task in self.load_all():
            if task.id == task_id:
                return task
        return None

    def upsert_task(self, task: GuidedTask) -> GuidedTask:
        tasks = self.load_all()
        for idx, existing in enumerate(tasks):
            if existing.id == task.id:
                tasks[idx] = task
                self.save_all(tasks)
                return task
        tasks.append(task)
        self.save_all(tasks)
        return task

    def create_task(self, title: str, prompt: str, steps: List[Dict[str, Any]], priority: int = 3) -> GuidedTask:
        task = GuidedTask(
            id=str(uuid.uuid4()),
            title=title,
            prompt=prompt,
            priority=priority,
            steps=[
                TaskStep(
                    id=step.get("id") or str(uuid.uuid4()),
                    instruction=step["instruction"],
                    expected_objects=step.get("expected_objects", []),
                    confirmation_type=step.get("confirmation_type", "user"),
                )
                for step in steps
            ],
        )
        return self.upsert_task(task)

    def start_task(self, task_id: str) -> Optional[GuidedTask]:
        tasks = self.load_all()
        selected = None
        for task in tasks:
            task.active = task.id == task_id
            if task.active:
                task.started_at = datetime.now().isoformat()
                task.completed_at = None
                task.current_step_index = 0
                for step in task.steps:
                    step.completed_at = None
                    step.completion_source = None
                selected = task
        self.save_all(tasks)
        if selected:
            self._log("task_started", {"task_id": selected.id, "title": selected.title})
        return selected

    def get_active_task(self) -> Optional[GuidedTask]:
        for task in self.load_all():
            if task.active and not task.completed_at:
                return task
        return None

    def complete_current_step(self, source: str = "user", notes: str = "") -> Optional[GuidedTask]:
        task = self.get_active_task()
        if not task or not task.current_step:
            return None
        step = task.current_step
        step.completed_at = datetime.now().isoformat()
        step.completion_source = source
        step.notes = notes
        self._log(
            "task_step_confirmed",
            {
                "task_id": task.id,
                "step_id": step.id,
                "source": source,
                "notes": notes,
            },
        )
        task.current_step_index += 1
        if task.current_step_index >= len(task.steps):
            task.completed_at = datetime.now().isoformat()
            task.active = False
            self._log("task_completed", {"task_id": task.id, "source": source})
        self.upsert_task(task)
        return task

    def skip_current_step(self, source: str = "user") -> Optional[GuidedTask]:
        return self.complete_current_step(source=source, notes="skipped")

    def _log(self, event_type: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
