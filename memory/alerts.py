"""
memory/alerts.py — Shared bridge between the camera app and the caregiver console.

The gesture interface (index.py ASSIST mode) fires emergency gestures (HELP,
PAIN, WATER, URGENT, ...). This module is the single place those events are
written, so the web app's caregiver console and the daily report can surface
them — instead of burying them in a flat text file nobody reads.

Everything stays on-device: these are JSONL lines in the local `memory/`
directory, same as the other runtime logs. Nothing leaves the machine.

  log_gesture_alert("HELP", 0.96)   ← called by the camera app
  list_gesture_alerts(limit=15)     ← called by the web app's caregiver console
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

GESTURE_ALERTS_PATH = os.path.join("memory", "gesture_alerts.jsonl")


def log_gesture_alert(gesture: str, confidence: float, demo: bool = False) -> None:
    """Append one emergency-gesture event to the shared caregiver-visible log.

    Never raises: a storage failure must not crash the camera loop.
    """
    try:
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "kind": "gesture",
            "gesture": str(gesture),
            "confidence": round(float(confidence), 3),
            "demo": bool(demo),
        }
        with open(GESTURE_ALERTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def list_gesture_alerts(limit: int = 50, hours: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return gesture alerts, newest first.

    `hours` filters to a rolling window (e.g. 24); `limit` caps the list size.
    Missing or corrupt lines are skipped defensively.
    """
    if not os.path.exists(GESTURE_ALERTS_PATH):
        return []
    cutoff = None
    if hours is not None:
        cutoff = datetime.now() - timedelta(hours=hours)
    entries: List[Dict[str, Any]] = []
    try:
        with open(GESTURE_ALERTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if cutoff is not None:
                    try:
                        if datetime.fromisoformat(e.get("ts", "")) < cutoff:
                            continue
                    except Exception:
                        continue
                entries.append(e)
    except Exception:
        return []
    return entries[-limit:][::-1]


def seed_demo_events() -> None:
    """Write a tiny, clearly-labelled DEMO dataset so `--demo` tells the whole
    story end-to-end on the caregiver dashboard: an object was taught (recall),
    an emergency gesture fired (HELP), and a safety event was recorded.

    All entries carry ``"demo": true`` so the console shows a DEMO pill and
    real events are never confused with demo ones. Runs only from
    ``memorymate.py --demo`` (skippable with ``--no-seed``).
    """
    # Idempotent: don't re-seed if a demo HELP already landed in the last hour.
    if any(e.get("demo") for e in list_gesture_alerts(hours=1)):
        return

    from memory.object_model import EnhancedMemoryVault
    from memory.safety_monitor import SafetyEvent

    # 1) Object taught → shows in "Recent recalls" as a matched recall.
    try:
        vault = EnhancedMemoryVault()
        vault.log_recall(obj_id="demo-medication-box", name="medication box",
                         confidence=0.94, matched=True, demo=True)
    except Exception:
        pass

    # 2) Emergency gesture → shows in "Emergency gestures" from the camera app.
    log_gesture_alert("HELP", 0.96, demo=True)

    # 3) Safety event → shows in "Safety events" (possible exit risk).
    try:
        from memory.safety_monitor import SAFETY_EVENTS_PATH
        ev = SafetyEvent(
            id="demo-exit-001",
            event_type="exit_risk",
            confidence="low",
            reason="Demo event: coat seen near the front door at night",
            action="ask caregiver to check in",
            facts={"demo": True},
        )
        with open(SAFETY_EVENTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev.to_dict()) + "\n")
    except Exception:
        pass
