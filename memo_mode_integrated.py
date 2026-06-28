"""
memo_mode.py — Integrated MEMO mode with ALL phases (1-5).
Teaching → Reminders → Caregiver Dashboard → Comfort → Family → Dementia UX
"""

import cv2
import numpy as np
import time
import pyttsx3
from typing import Optional, List
from enum import Enum

# Phase 1: Core memory
from memory.object_model import EnhancedMemoryVault, PersonalObject
from memory.teach_module import TeachSession

# Phase 2: Reminders
from memory.reminders import RoutineReminder, VoiceCue, ReminderType
from memory.routines import AdvancedRoutineStore

# Phase 4: Advanced features
from memory.comfort_mode import ComfortMode, SpatialMemory
from memory.family_relations import FamilyTree, FamilyMember, FamilyIntegration
from memory.patient_profile import PatientProfileStore
from memory.safety_monitor import SafetyMonitor
from memory.task_guidance import GuidedTaskStore

# Phase 5: UX
from memory.phase5_ux import DementiaUX


class MemoState(Enum):
    """MEMO mode states."""
    RECALL = "recall"           # Show stored objects
    TEACH = "teach"             # Teach new object
    FAMILY = "family"           # View family
    COMFORT = "comfort"         # Emotional support
    ROUTINES = "routines"       # Check daily routines
    BROWSE = "browse"           # Browse all objects
    TASK_GUIDE = "task_guide"   # Step-by-step task support


class MemoSession:
    """Integrated MEMO mode with all phases."""
    
    def __init__(self, tts_engine=None):
        # Phase 1: Memory
        self.vault = EnhancedMemoryVault()
        self.teach_session: Optional[TeachSession] = None
        
        # Phase 2: Reminders
        self.reminders = RoutineReminder(self.vault, tts_engine)
        self.advanced_routines = AdvancedRoutineStore()
        self.task_store = GuidedTaskStore()
        
        # Phase 4: Advanced
        self.comfort = ComfortMode(tts_engine)
        self.spatial = SpatialMemory()
        self.family_tree = FamilyTree()
        self.family_integration = FamilyIntegration(tts_engine)
        self.profile_store = PatientProfileStore()
        self.profile = self.profile_store.load()
        self.safety = SafetyMonitor(profile=self.profile)
        
        # Phase 5: UX
        self.ux = DementiaUX(frame_width=640, frame_height=480)
        
        # TTS engine
        self.tts = tts_engine or pyttsx3.init()
        self.tts.setProperty('rate', 100)  # Calm voice
        
        # State
        self.state = MemoState.RECALL
        self.sub_state = ""
        self.status_msg = f"Hello {self.profile.preferred_name}. Choose an activity."
        self.last_action = time.time()
        self.selected_option = 0
        self.last_advanced_prompt = 0.0
        self.advanced_prompt_cooldown = 300.0
    
    def update(self, frame: np.ndarray, hand_present: bool = False) -> np.ndarray:
        """Process one frame in MEMO mode."""
        
        # Check for time-based reminders
        self._check_reminders()
        
        # Route to current state
        if self.state == MemoState.RECALL:
            frame = self._recall_state(frame, hand_present)
        elif self.state == MemoState.TEACH:
            frame = self._teach_state(frame, hand_present)
        elif self.state == MemoState.FAMILY:
            frame = self._family_state(frame, hand_present)
        elif self.state == MemoState.COMFORT:
            frame = self._comfort_state(frame, hand_present)
        elif self.state == MemoState.ROUTINES:
            frame = self._routines_state(frame, hand_present)
        elif self.state == MemoState.BROWSE:
            frame = self._browse_state(frame, hand_present)
        elif self.state == MemoState.TASK_GUIDE:
            frame = self._task_guide_state(frame, hand_present)
        
        # Draw UI overlay (Phase 5 UX)
        frame = self._draw_overlay(frame)
        
        return frame

    def speak(self, message: str, rate: Optional[int] = None):
        """Speak a short prompt with profile-aware voice speed."""
        if not message:
            return
        try:
            self.tts.setProperty('rate', rate or self.profile.calm_voice_rate)
            self.tts.say(message)
            self.tts.runAndWait()
        except Exception:
            pass
    
    def _recall_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 1: Recall stored objects."""
        
        objects = self.vault.list_objects()
        if not objects:
            frame = self.ux.show_validation_feedback(
                frame, "No objects learned yet. Try TEACH.", "warning")
            return frame
        
        # Show menu
        options = [o.name[:15] for o in objects[:4]]
        options.append("Back")
        
        frame = self.ux.draw_simple_menu(frame, options, self.selected_option)
        frame = self.ux.draw_action_instructions(frame, "👆 Select object to remember")
        
        return frame
    
    def _teach_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 1: Teach new object with calm guidance."""
        
        if not self.teach_session:
            self.teach_session = TeachSession(self.vault, self.tts)
        
        # Update teaching
        frame = self.teach_session.update(frame, hand_present)
        
        # Check if teaching completed
        if hasattr(self.teach_session, 'state') and self.teach_session.state == "SAVED":
            self.tts.say("Great job! Your object is saved.")
            self.tts.runAndWait()
            frame = self.ux.show_validation_feedback(frame, "Object saved!", "success")
            self.teach_session = None
            time.sleep(2)
            self.state = MemoState.RECALL
        
        return frame
    
    def _family_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 4: View and interact with family."""
        
        members = self.family_tree.get_all_members()
        if not members:
            frame = self.ux.show_validation_feedback(
                frame, "No family members added yet.", "info")
            return frame
        
        # Show family gallery
        frame = self.comfort.show_family_gallery(frame)
        
        # Show overdue members
        overdue = self.family_tree.get_overdue_members()
        if overdue:
            msg = f"Your {overdue[0].relation} {overdue[0].name} is visiting soon!"
            frame = self.ux.show_validation_feedback(frame, msg, "info")
        
        return frame
    
    def _comfort_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 4: Emotional comfort mode."""
        
        if not self.comfort.active:
            self.comfort.activate_comfort_mode("anxiety")
        
        frame = self.comfort.show_family_gallery(frame)
        frame = self.ux.draw_calm_frame(frame, show_comfort_mode=True)
        frame = self.ux.show_validation_feedback(
            frame, "You are safe and loved. Breathe deeply.", "success")
        
        return frame

    def _task_guide_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Advanced: one-step-at-a-time task guidance."""

        task = self.task_store.get_active_task()
        if not task:
            tasks = self.task_store.load_all()
            if not tasks:
                frame = self.ux.show_validation_feedback(frame, "No guided tasks configured.", "info")
                return frame
            options = [task.title[:16] for task in tasks[:3]] + ["Back"]
            frame = self.ux.draw_simple_menu(frame, options, self.selected_option)
            frame = self.ux.draw_action_instructions(frame, "Choose a task")
            self.status_msg = "A caregiver can start tasks from the dashboard."
            return frame

        step = task.current_step
        if not step:
            frame = self.ux.show_validation_feedback(frame, "Task complete.", "success")
            return frame

        progress_current = min(task.current_step_index + 1, len(task.steps))
        frame = self.ux.show_progress_indicator(
            frame,
            progress_current,
            len(task.steps),
            task.title,
        )

        cv2.rectangle(frame, (25, 165), (self.ux.frame_width - 25, 295), (255, 255, 255), -1)
        cv2.rectangle(frame, (25, 165), (self.ux.frame_width - 25, 295), (44, 62, 80), 3)
        cv2.putText(frame, step.instruction[:56], (45, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                   self.ux.COLORS["text_primary"], 2)

        button_y = 330
        frame = self.ux.draw_large_button(frame, 45, button_y, "Done", 155, 65)
        frame = self.ux.draw_large_button(frame, 240, button_y, "Help", 155, 65)
        frame = self.ux.draw_large_button(frame, 435, button_y, "Skip", 155, 65)
        self.status_msg = "Use Done, Help, or Skip. Caregiver confirmations are logged."
        return frame
    
    def _routines_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 2: Daily routine reminders."""
        
        due_steps = self.advanced_routines.due_steps()
        if not due_steps:
            frame = self.ux.show_validation_feedback(
                frame, "No routines need attention right now.", "info")
            return frame
        
        y = 100
        for routine, step in due_steps[:4]:
            text = f"{routine.name}: {step.title}"
            cv2.putText(frame, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                       (0, 255, 0), 2)
            y += 50
        
        return frame
    
    def _browse_state(self, frame: np.ndarray, hand_present: bool) -> np.ndarray:
        """Phase 1: Browse all objects with spatial memory."""
        
        objects = self.vault.list_objects()
        
        # Draw spatial overlay if available
        frame = self.spatial.draw_spatial_overlay(frame)
        
        # Show stats
        stats = f"📦 {len(objects)} objects | "
        high_priority = len([o for o in objects if o.importance >= 4])
        stats += f"💊 {high_priority} high priority"
        
        cv2.putText(frame, stats, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                   (0, 255, 0), 2)
        
        # Show recent objects
        y = 100
        for obj in objects[-3:]:
            text = f"• {obj.name} ({obj.importance}/5) - {obj.location}"
            cv2.putText(frame, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       (200, 200, 200), 1)
            y += 35
        
        return frame
    
    def _check_reminders(self):
        """Check for and play time-based reminders."""
        
        reminder = self.reminders.check_time_reminders()
        if reminder:
            reminder.speak(self.tts)

        now = time.time()
        if now - self.last_advanced_prompt < self.advanced_prompt_cooldown:
            return

        due_steps = self.advanced_routines.due_steps()
        if due_steps:
            _, step = due_steps[0]
            self.last_advanced_prompt = now
            self.speak(step.prompt or step.title)

    def start_guided_task(self, task_id: str) -> bool:
        """Start a guided task, usually from caregiver dashboard."""
        task = self.task_store.start_task(task_id)
        if not task:
            return False
        self.state = MemoState.TASK_GUIDE
        self.speak(task.prompt or task.title)
        return True

    def complete_guided_step(self, source: str = "user") -> bool:
        task = self.task_store.complete_current_step(source=source)
        return task is not None

    def trigger_comfort(self, emotion: str = "anxiety"):
        self.state = MemoState.COMFORT
        self.comfort.activate_comfort_mode(emotion)

    def evaluate_safety_context(self, detected_objects: Optional[List[str]] = None,
                                room: Optional[str] = None,
                                near_exit: bool = False):
        event = self.safety.evaluate_context(detected_objects, room=room, near_exit=near_exit)
        if event:
            self.speak("Let's pause for a moment. You are safe here.")
        return event
    
    def _draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw status overlay and menu (Phase 5 UX)."""
        
        # Draw state label
        state_label = f"MEMO: {self.state.value.upper()}"
        frame = self.ux.draw_action_instructions(frame, state_label)
        
        # Draw status at bottom
        cv2.rectangle(frame, (0, frame.shape[0] - 40), (frame.shape[1], frame.shape[0]),
                     self.ux.COLORS["background"], -1)
        cv2.putText(frame, self.status_msg, (20, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.ux.COLORS["text_primary"], 2)
        
        return frame
    
    def switch_state(self, new_state: MemoState):
        """Switch to different MEMO state."""
        self.state = new_state
        self.selected_option = 0
        
        # Announce state change
        msg = f"Switching to {new_state.value}"
        self.tts.say(msg)
        self.tts.runAndWait()
    
    def get_menu_options(self) -> List[str]:
        """Get main menu options."""
        return [
            "Recall Objects",
            "Teach New",
            "View Family",
            "Comfort Mode",
            "Routines",
            "Guided Task",
            "Browse All",
        ]


class QuickMemoMenu:
    """Quick menu for MEMO mode selection (Phase 5 UX)."""
    
    def __init__(self, ux: DementiaUX):
        self.ux = ux
        self.options = [
            ("Recall", MemoState.RECALL),
            ("Teach", MemoState.TEACH),
            ("Family", MemoState.FAMILY),
            ("Comfort", MemoState.COMFORT),
            ("Tasks", MemoState.TASK_GUIDE),
        ]
    
    def draw(self, frame: np.ndarray, selected_idx: int = 0) -> np.ndarray:
        """Draw main menu with large buttons."""
        
        button_width = 180
        button_height = 60
        x_start = 50
        y_start = 150
        x_spacing = 220
        
        for idx, (label, _) in enumerate(self.options):
            x = x_start + (idx % 2) * x_spacing
            y = y_start + (idx // 2) * 100
            
            is_selected = (idx == selected_idx)
            frame = self.ux.draw_large_button(frame, x, y, label, button_width,
                                             button_height, is_selected)
        
        return frame
