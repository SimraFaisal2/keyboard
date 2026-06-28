"""
phase5_ux.py — Phase 5: Dementia-friendly UX enhancements throughout.
Large buttons, high contrast, simple choices, calm feedback, no errors.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


class DementiaUX:
    """Dementia-friendly UI components and principles."""
    
    # UX Constants
    LARGE_BUTTON_HEIGHT = 60
    LARGE_BUTTON_WIDTH = 200
    MIN_TAP_SIZE = 48  # Minimum touch target size (pixels)
    HIGH_CONTRAST_THRESHOLD = 150
    
    # Colors for high contrast
    COLORS = {
        "background": (240, 240, 240),      # Light gray
        "button_normal": (52, 152, 219),    # Calm blue
        "button_hover": (41, 128, 185),     # Darker blue
        "button_disabled": (149, 165, 166), # Gray
        "text_primary": (44, 62, 80),       # Dark blue-gray
        "text_secondary": (127, 140, 141),  # Medium gray
        "success": (39, 174, 96),           # Green
        "warning": (241, 196, 15),          # Yellow
        "error": (231, 76, 60),             # Red (minimal use)
        "accent": (155, 89, 182),           # Purple
    }
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.hover_target = None
        self.hover_time = 0.0
        self.last_action_feedback = ""
    
    def draw_large_button(self, frame: np.ndarray, x: int, y: int, 
                         text: str, width: int = 200, height: int = 60,
                         is_hovered: bool = False) -> np.ndarray:
        """Draw large, high-contrast button for easy clicking."""
        
        # Button color
        color = self.COLORS["button_hover"] if is_hovered else self.COLORS["button_normal"]
        
        # Draw button rectangle (thick border for visibility)
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, -1)
        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 0), 3)  # Border
        
        # Draw text (large, centered)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        thickness = 2
        
        # Get text size to center
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = x + (width - text_size[0]) // 2
        text_y = y + (height + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale,
                   (255, 255, 255), thickness)  # White text
        
        return frame
    
    def draw_simple_menu(self, frame: np.ndarray, options: List[str],
                        selection_index: int = 0) -> np.ndarray:
        """Draw simple menu with 2-4 options (not more)."""
        
        if len(options) > 4:
            options = options[:4]  # Max 4 options
        
        # Draw title area
        cv2.rectangle(frame, (0, 0), (self.frame_width, 50), 
                     self.COLORS["background"], -1)
        cv2.putText(frame, "Choose one:", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, self.COLORS["text_primary"], 2)
        
        # Draw option buttons
        button_width = (self.frame_width - 40) // len(options)
        button_height = self.LARGE_BUTTON_HEIGHT
        
        for idx, option in enumerate(options):
            x = 20 + idx * (button_width + 10)
            y = 70
            is_selected = (idx == selection_index)
            
            color = self.COLORS["accent"] if is_selected else self.COLORS["button_normal"]
            cv2.rectangle(frame, (x, y), (x + button_width - 10, y + button_height),
                         color, -1)
            cv2.rectangle(frame, (x, y), (x + button_width - 10, y + button_height),
                         (0, 0, 0), 3)
            
            # Text
            text_size = cv2.getTextSize(option, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            text_x = x + (button_width - 10 - text_size[0]) // 2
            text_y = y + (button_height + text_size[1]) // 2
            cv2.putText(frame, option, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return frame
    
    def show_validation_feedback(self, frame: np.ndarray, message: str,
                                 feedback_type: str = "success") -> np.ndarray:
        """Show validation feedback instead of errors."""
        
        # feedback_type: "success", "info", "warning"
        colors_map = {
            "success": self.COLORS["success"],
            "info": self.COLORS["button_normal"],
            "warning": self.COLORS["warning"],
        }
        color = colors_map.get(feedback_type, self.COLORS["success"])
        
        # Draw feedback box at bottom
        box_height = 80
        y_start = self.frame_height - box_height
        
        cv2.rectangle(frame, (0, y_start), (self.frame_width, self.frame_height),
                     color, -1)
        cv2.rectangle(frame, (0, y_start), (self.frame_width, self.frame_height),
                     (0, 0, 0), 3)
        
        # Friendly message with emoji
        emojis = {
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️",
        }
        emoji = emojis.get(feedback_type, "✅")
        full_message = f"{emoji} {message}"
        
        text_size = cv2.getTextSize(full_message, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (self.frame_width - text_size[0]) // 2
        text_y = y_start + 50
        
        cv2.putText(frame, full_message, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def show_progress_indicator(self, frame: np.ndarray, current: int, 
                               total: int, message: str = "") -> np.ndarray:
        """Show progress bar for multi-step processes."""
        
        # Draw progress bar
        bar_width = 300
        bar_height = 20
        bar_x = (self.frame_width - bar_width) // 2
        bar_y = 100
        
        # Background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     self.COLORS["button_disabled"], -1)
        
        # Progress fill
        if total > 0:
            progress = int((current / total) * bar_width)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress, bar_y + bar_height),
                         self.COLORS["success"], -1)
        
        # Border
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (0, 0, 0), 2)
        
        # Text
        progress_text = f"{current}/{total}"
        text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (self.frame_width - text_size[0]) // 2
        text_y = bar_y + 35
        cv2.putText(frame, progress_text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, self.COLORS["text_primary"], 2)
        
        if message:
            msg_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            msg_x = (self.frame_width - msg_size[0]) // 2
            msg_y = text_y + 40
            cv2.putText(frame, message, (msg_x, msg_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, self.COLORS["text_secondary"], 2)
        
        return frame
    
    def draw_action_instructions(self, frame: np.ndarray, instruction: str,
                                 hold_time: Optional[float] = None) -> np.ndarray:
        """Show clear action instructions."""
        
        # Draw instruction box at top
        cv2.rectangle(frame, (0, 0), (self.frame_width, 60),
                     self.COLORS["accent"], -1)
        
        # Main instruction
        text_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
        text_x = (self.frame_width - text_size[0]) // 2
        cv2.putText(frame, instruction, (text_x, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # If hold time required, show it
        if hold_time:
            hold_text = f"Hold for {hold_time:.1f}s"
            hold_size = cv2.getTextSize(hold_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
            hold_x = self.frame_width - hold_size[0] - 10
            cv2.putText(frame, hold_text, (hold_x, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        
        return frame
    
    def draw_calm_frame(self, frame: np.ndarray, show_comfort_mode: bool = False) -> np.ndarray:
        """Apply calming visual design to frame."""
        
        if show_comfort_mode:
            # Slightly desaturate and warm colors for comfort mode
            # Reduce blue channel slightly
            frame[:, :, 0] = np.clip(frame[:, :, 0] * 0.95, 0, 255).astype(np.uint8)
        
        return frame
    
    @staticmethod
    def get_dementia_ux_principles() -> dict:
        """Return UX principles for dementia care interface."""
        return {
            "large_buttons": "Min 48px touch targets, 60px+ recommended",
            "high_contrast": "Dark text on light, or light text on dark",
            "few_choices": "Max 3-4 options at a time, not 10+",
            "clear_feedback": "Every action gets voice + visual confirmation",
            "no_errors": "Validate gently, redirect instead of scold",
            "consistent_layout": "Buttons always in same place",
            "calm_voice": "100 WPM (slow), reassuring tone",
            "large_text": "18pt+ font size minimum",
            "simple_icons": "Clear, high-contrast icons + text labels",
            "undo_window": "15-second window to cancel actions",
            "no_hidden_options": "All important actions visible",
            "familiar_colors": "Calming blues, greens; avoid red unless urgent",
        }
