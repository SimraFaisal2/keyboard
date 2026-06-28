"""
Patient profile and caregiver preferences for dementia support.

This module keeps personalization local and explicit. The app can use these
settings for prompts, comfort mode, routines, and safety checks without hard
coding patient-specific details into runtime code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional


PROFILE_PATH = os.path.join("memory", "patient_profile.json")


@dataclass
class PatientProfile:
    preferred_name: str = "friend"
    primary_language: str = "en"
    calm_voice_rate: int = 100
    caregiver_name: str = ""
    caregiver_phone: str = ""
    emergency_contact: str = ""
    high_risk_times: List[Dict[str, str]] = field(
        default_factory=lambda: [{"start": "17:00", "end": "21:00"}]
    )
    exit_risk_enabled: bool = True
    comfort_preferences: List[str] = field(
        default_factory=lambda: ["family photos", "calm voice", "familiar music"]
    )
    known_triggers: List[str] = field(default_factory=list)
    safe_places: List[str] = field(default_factory=lambda: ["living room", "kitchen"])
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PatientProfileStore:
    def __init__(self, path: str = PROFILE_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self) -> PatientProfile:
        if not os.path.exists(self.path):
            profile = PatientProfile()
            self.save(profile)
            return profile

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PatientProfile(**data)
        except Exception:
            backup_path = f"{self.path}.invalid"
            try:
                os.replace(self.path, backup_path)
            except OSError:
                pass
            profile = PatientProfile()
            self.save(profile)
            return profile

    def save(self, profile: PatientProfile) -> PatientProfile:
        profile.updated_at = datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        return profile

    def update(self, updates: Dict[str, Any]) -> PatientProfile:
        profile = self.load()
        valid_keys = set(profile.to_dict().keys())
        for key, value in updates.items():
            if key in valid_keys and key != "updated_at":
                setattr(profile, key, value)
        return self.save(profile)


def get_patient_profile(path: Optional[str] = None) -> PatientProfile:
    return PatientProfileStore(path or PROFILE_PATH).load()
