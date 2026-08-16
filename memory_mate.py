"""
memory_mate.py — MemoryMate: a patient-first dementia support app
=================================================================
A single, local web app that turns the existing memory modules into something
a person with dementia (and their caregiver) can actually use on a tablet or PC.

Patient side  (big buttons, calm voice, no errors)
  /            – home: greeting + one-tap activities + live alert banner
  /objects     – "Where's my stuff?"  (tap an object → says where it is)
  /family      – family gallery with spoken introductions
  /comfort     – one-tap emotional support (anxious / confused / agitated / lonely)
  /tasks       – guided tasks, one step at a time (Done / Help / Skip)
  /today       – today's reminders and routine steps

Caregiver side
  /caregiver   – console: add objects & family, start tasks, trigger comfort,
                 report safety context, view alerts & activity log

Everything runs locally. Voice (pyttsx3) is best-effort: if it fails, the
screen still shows every message. The app never blocks on speech.

Run:  python memory_mate.py   →  http://localhost:5000
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, jsonify, render_template, request

from memory.object_model import EnhancedMemoryVault
from memory.reminders import RoutineReminder
from memory.family_relations import FamilyTree, FamilyMember
from memory.comfort_mode import ComfortMode
from memory.patient_profile import PatientProfileStore
from memory.safety_monitor import SafetyMonitor
from memory.task_guidance import GuidedTaskStore
from memory.routines import AdvancedRoutineStore, check_morning_prompt
from memory.alerts import list_gesture_alerts

CALM_RATE = 100   # slow, reassuring voice


class _SilentTTS:
    """No-op TTS so modules never speak outside the single voice queue."""
    def setProperty(self, *a, **k):
        pass
    def getProperty(self, *a, **k):
        return CALM_RATE
    def say(self, *a, **k):
        pass
    def runAndWait(self, *a, **k):
        pass


class Voice:
    """Non-blocking, serialized text-to-speech. Failures are silent."""

    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None

    def _ensure(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", CALM_RATE)
        return self._engine

    def speak(self, text):
        if not text:
            return
        def _run():
            try:
                with self._lock:
                    eng = self._ensure()
                    eng.say(text)
                    eng.runAndWait()
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()


class MemoryMate:
    def __init__(self, data_dir: str = "memory", start_threads: bool = True):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.voice = Voice()
        self.profile_store = PatientProfileStore(path=os.path.join(data_dir, "patient_profile.json"))
        self.profile = self.profile_store.load()

        self.vault = EnhancedMemoryVault(base_path=data_dir)
        self.reminders = RoutineReminder(self.vault, tts_engine=_SilentTTS())
        self.reminders.log_file = os.path.join(data_dir, "activity_log.jsonl")

        self.family_tree = FamilyTree()
        self.family_tree.db_file = os.path.join(data_dir, "family_tree.json")

        self.comfort = ComfortMode(tts_engine=_SilentTTS())
        self.comfort.family_relations = self._load_json(
            os.path.join(data_dir, "family_relations.json"), {})

        self.tasks = GuidedTaskStore(path=os.path.join(data_dir, "guided_tasks.json"),
                                     log_path=os.path.join(data_dir, "task_log.jsonl"))
        self.routines = AdvancedRoutineStore(path=os.path.join(data_dir, "advanced_routines.json"))
        self.safety = SafetyMonitor(events_path=os.path.join(data_dir, "safety_events.jsonl"),
                                    profile=self.profile)

        # live alert (text the patient page polls)
        self.current_alert = None          # {text, kind, time}
        self.alert_history = []            # most recent first
        self._lock = threading.Lock()

        if start_threads:
            self._start_reminder_thread()

    def check_reminders_once(self):
        """Run one reminder sweep (used by tests and on demand)."""
        cue = self.reminders.check_time_reminders()
        if cue:
            self._say(cue.message, "reminder")
        for routine, step in self.routines.due_steps():
            msg = step.prompt or f"{routine.name}: {step.title}"
            self._say(msg, "routine")
            return
        return None

    @staticmethod
    def _load_json(path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    # ─── Alert handling ─────────────────────────────────────────────────────
    def _set_alert(self, text, kind="info"):
        alert = {"text": text, "kind": kind,
                 "time": datetime.now().strftime("%H:%M")}
        with self._lock:
            self.current_alert = alert
            self.alert_history.insert(0, alert)
            self.alert_history = self.alert_history[:30]
        return alert

    def _say(self, text, kind="info"):
        """Speak + store as the current alert (voice and visual, always)."""
        self.voice.speak(text)
        return self._set_alert(text, kind)

    # ─── Reminder thread ────────────────────────────────────────────────────
    def _start_reminder_thread(self):
        def loop():
            last_routine_announce = {}
            while True:
                try:
                    cue = self.reminders.check_time_reminders()
                    if cue:
                        self._say(cue.message, "reminder")

                    greeting = check_morning_prompt(self.profile.preferred_name)
                    if greeting:
                        self._say(greeting, "greeting")

                    for routine, step in self.routines.due_steps():
                        key = step.id
                        if time.time() - last_routine_announce.get(key, 0) > 1800:
                            last_routine_announce[key] = time.time()
                            msg = step.prompt or f"{routine.name}: {step.title}"
                            self._say(msg, "routine")
                            break
                except Exception:
                    pass
                time.sleep(20)
        threading.Thread(target=loop, daemon=True).start()

    # ─── Patient pages ──────────────────────────────────────────────────────
    def page_home(self):
        return render_template("patient.html", page="home",
                               name=self.profile.preferred_name)

    def page_objects(self):
        objs = sorted(self.vault.list_objects(), key=lambda o: o.name.lower())
        return render_template("patient.html", page="objects",
                               name=self.profile.preferred_name, objects=objs)

    def page_family(self):
        members = self.family_tree.get_all_members()
        return render_template("patient.html", page="family",
                               name=self.profile.preferred_name, members=members)

    def page_comfort(self):
        return render_template("patient.html", page="comfort",
                               name=self.profile.preferred_name)

    def page_tasks(self):
        task = self.tasks.get_active_task()
        return render_template("patient.html", page="tasks",
                               name=self.profile.preferred_name, task=task)

    def page_today(self):
        reminders = [{
            "label": rt.value.upper(),
            "time": f"{r['time'][0]:02d}:{r['time'][1]:02d}",
            "enabled": r["enabled"],
            "prompt": r["prompts"][0],
        } for rt, r in self.reminders.routines.items()]
        due = [(routine, step) for routine, step in self.routines.due_steps()]
        high = [o for o in self.vault.list_objects() if o.importance >= 4]
        return render_template("patient.html", page="today",
                               name=self.profile.preferred_name,
                               reminders=reminders, due=due, high=high)

    # ─── Caregiver console ──────────────────────────────────────────────────
    def page_caregiver(self):
        gesture_alerts = list_gesture_alerts(limit=20)
        stats = {
            "objects": len(self.vault.list_objects()),
            "family": len(self.family_tree.get_all_members()),
            "overdue": len(self.family_tree.get_overdue_members()),
            "tasks": len(self.tasks.load_all()),
            "gestures": len(list_gesture_alerts(hours=24)),
        }
        return render_template("caregiver.html", stats=stats,
                               objects=sorted(self.vault.list_objects(),
                                              key=lambda o: o.name.lower()),
                               members=self.family_tree.get_all_members(),
                               tasks=self.tasks.load_all(),
                               active_task=self.tasks.get_active_task(),
                               routines=self.routines.load_all(),
                               alerts=self.alert_history,
                               activities=self.reminders.get_activity_log(hours=48),
                               gesture_alerts=gesture_alerts,
                               recalls=self.vault.recent_recalls(15),
                               recall_stats=self.vault.recall_stats(days=7),
                               safety_events=[e.to_dict()
                                              for e in self.safety.list_events(limit=10)],
                               name=self.profile.preferred_name)

    def api_live(self):
        """Live polling endpoint for the caregiver console: returns everything
        the camera app and safety monitor have written since the page loaded."""
        return jsonify({
            "gesture_alerts": list_gesture_alerts(limit=20),
            "recalls": self.vault.recent_recalls(15),
            "safety_events": [e.to_dict()
                               for e in self.safety.list_events(limit=10)],
            "activities": self.reminders.get_activity_log(hours=48),
            "alert": self.current_alert,
        })

    # ─── API: patient actions ───────────────────────────────────────────────
    def api_object_locate(self):
        name = (request.json or {}).get("name", "").strip()
        obj = next((o for o in self.vault.list_objects()
                    if o.name.lower() == name.lower()), None)
        if not obj:
            return jsonify({"error": "object not found"}), 404
        loc = obj.location or "somewhere I haven't recorded yet"
        verb = "are" if obj.name.lower().endswith("s") else "is"
        text = f"Your {obj.name} {verb} {loc}."
        self._say(text, "object")
        return jsonify({"text": text})

    def api_comfort(self):
        emotion = (request.json or {}).get("emotion", "anxiety")
        message = self.comfort.activate_comfort_mode(emotion)
        self._say(message, "comfort")
        return jsonify({"text": message})

    def api_task_action(self, action):
        task = self.tasks.get_active_task()
        if not task:
            return jsonify({"error": "no active task"}), 404
        if action == "done":
            task = self.tasks.complete_current_step(source="user")
        elif action == "help":
            self.reminders.log_activity("task_help", {"task": task.title})
            self._say("Let's take our time. You are doing great.")
            return jsonify({"text": "Help requested — caregiver has been notified.",
                            "task": self._task_payload(task)})
        elif action == "skip":
            task = self.tasks.complete_current_step(source="user", notes="skipped")
        if task and task.completed_at:
            self._say("Well done! Task complete.")
        return jsonify({"task": self._task_payload(task)})

    def api_alert_dismiss(self):
        with self._lock:
            self.current_alert = None
        return jsonify({"ok": True})

    def api_speak(self):
        text = (request.json or {}).get("text", "").strip()
        if text:
            self._say(text, "spoken")
        return jsonify({"ok": True})

    # ─── API: caregiver actions ─────────────────────────────────────────────
    def api_object_add(self):
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        importance = int(data.get("importance") or 2)
        ok = self.vault.add_object(
            name=name,
            note=data.get("note", ""),
            is_medication=bool(data.get("is_medication")),
        )
        if not ok:
            return jsonify({"error": "could not save object"}), 500
        obj = next(o for o in self.vault.list_objects() if o.name.lower() == name.lower())
        obj.location = data.get("location", "unknown")
        obj.importance = importance
        self.vault.add_object(obj)
        self.reminders.log_activity("object_added", {"name": name})
        return jsonify({"ok": True})

    def api_family_add(self):
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        member = FamilyMember(
            id=data.get("id") or name.lower().replace(" ", "_"),
            name=name,
            relation=data.get("relation", "family"),
            phone=data.get("phone"),
            email=data.get("email"),
            bio=data.get("bio"),
        )
        if not self.family_tree.add_member(member):
            return jsonify({"error": "member already exists"}), 400
        return jsonify({"ok": True})

    def api_family_visit(self, member_id):
        ok = self.family_tree.record_visit(member_id)
        if not ok:
            return jsonify({"error": "member not found"}), 404
        member = self.family_tree.get_member(member_id)
        if member:
            self._say(self.family_tree.create_greeting_message(member_id), "family")
        return jsonify({"ok": True})

    def api_task_start(self, task_id):
        task = self.tasks.start_task(task_id)
        if not task:
            return jsonify({"error": "task not found"}), 404
        msg = task.prompt or f"Let's start: {task.title}"
        self._say(msg, "task")
        return jsonify({"task": self._task_payload(task)})

    def api_safety(self):
        data = request.json or {}
        detected = [s.strip() for s in (data.get("detected_objects") or "").split(",") if s.strip()]
        event = self.safety.evaluate_context(
            detected_objects=detected,
            room=data.get("room"),
            near_exit=bool(data.get("near_exit")),
        )
        if event:
            self._say("Let's pause for a moment. You are safe here.", "safety")
            return jsonify({"event": event.to_dict()})
        return jsonify({"event": None})

    def api_profile(self):
        data = request.json or {}
        name = data.get("preferred_name", "").strip()
        if name:
            self.profile = self.profile_store.update({"preferred_name": name})
        return jsonify({"ok": True, "name": self.profile.preferred_name})

    # ─── JSON helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _task_payload(task):
        if not task:
            return None
        step = task.current_step
        return {
            "id": task.id,
            "title": task.title,
            "step_index": task.current_step_index + 1,
            "step_total": len(task.steps),
            "instruction": step.instruction if step else None,
            "complete": task.is_complete,
        }

    def api_state(self):
        with self._lock:
            alert = self.current_alert
        return jsonify({
            "alert": alert,
            "alert_history": self.alert_history[:10],
            "stats": {
                "objects": len(self.vault.list_objects()),
                "family": len(self.family_tree.get_all_members()),
            },
        })


def create_app(data_dir: str = "memory") -> MemoryMate:
    app = Flask(__name__)
    mate = MemoryMate(data_dir)

    # Patient pages
    app.add_url_rule("/", "home", mate.page_home)
    app.add_url_rule("/objects", "objects", mate.page_objects)
    app.add_url_rule("/family", "family", mate.page_family)
    app.add_url_rule("/comfort", "comfort", mate.page_comfort)
    app.add_url_rule("/tasks", "tasks", mate.page_tasks)
    app.add_url_rule("/today", "today", mate.page_today)
    app.add_url_rule("/caregiver", "caregiver", mate.page_caregiver)

    # API
    app.add_url_rule("/api/state", "api_state", mate.api_state)
    app.add_url_rule("/api/live", "api_live", mate.api_live)
    app.add_url_rule("/api/alert/dismiss", "api_alert_dismiss",
                     mate.api_alert_dismiss, methods=["POST"])
    app.add_url_rule("/api/speak", "api_speak", mate.api_speak, methods=["POST"])
    app.add_url_rule("/api/object/locate", "api_object_locate",
                     mate.api_object_locate, methods=["POST"])
    app.add_url_rule("/api/comfort", "api_comfort", mate.api_comfort, methods=["POST"])
    app.add_url_rule("/api/tasks/done", "api_task_done",
                     lambda: mate.api_task_action("done"), methods=["POST"])
    app.add_url_rule("/api/tasks/help", "api_task_help",
                     lambda: mate.api_task_action("help"), methods=["POST"])
    app.add_url_rule("/api/tasks/skip", "api_task_skip",
                     lambda: mate.api_task_action("skip"), methods=["POST"])
    app.add_url_rule("/api/object/add", "api_object_add",
                     mate.api_object_add, methods=["POST"])
    app.add_url_rule("/api/family/add", "api_family_add",
                     mate.api_family_add, methods=["POST"])
    app.add_url_rule("/api/family/<member_id>/visit", "api_family_visit",
                     mate.api_family_visit, methods=["POST"])
    app.add_url_rule("/api/tasks/start/<task_id>", "api_task_start",
                     mate.api_task_start, methods=["POST"])
    app.add_url_rule("/api/safety", "api_safety", mate.api_safety, methods=["POST"])
    app.add_url_rule("/api/profile", "api_profile", mate.api_profile, methods=["POST"])

    mate.app = app
    return mate


def main():
    mate = create_app()
    print("🧠 MemoryMate starting...")
    print("📱 Patient app : http://localhost:5000")
    print("🩺 Caregiver   : http://localhost:5000/caregiver")
    mate.app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
