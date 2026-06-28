"""
family_relations.py — Phase 4: Family tree and relationship management.
Track family members, relationships, contact info, visit history.
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime, date
from dataclasses import dataclass, asdict
import pyttsx3


@dataclass
class FamilyMember:
    """Represents a family member."""
    id: str
    name: str
    relation: str  # "daughter", "grandson", "sister", etc.
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_path: Optional[str] = None
    voice_greeting_path: Optional[str] = None
    bio: Optional[str] = None  # "Lives in California, loves gardening"
    visit_frequency: str = "weekly"  # "daily", "weekly", "monthly"
    last_visit: Optional[str] = None
    visits: List[str] = None  # ISO datetime strings
    created_at: str = None
    
    def __post_init__(self):
        if self.visits is None:
            self.visits = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        return data
    
    def is_overdue_for_visit(self) -> bool:
        """Check if family member is overdue based on visit frequency."""
        if not self.last_visit:
            return True
        
        last_visit_date = datetime.fromisoformat(self.last_visit).date()
        today = date.today()
        days_since = (today - last_visit_date).days
        
        frequency_days = {
            "daily": 1,
            "weekly": 7,
            "bi-weekly": 14,
            "monthly": 30,
        }
        
        threshold = frequency_days.get(self.visit_frequency, 30)
        return days_since > threshold


class FamilyTree:
    """Manage family relationships and tree structure."""
    
    def __init__(self):
        self.members: Dict[str, FamilyMember] = {}
        self.relationships: Dict[str, List[str]] = {}  # member_id -> [related_ids]
        self.db_file = "memory/family_tree.json"
        self._load()
    
    def _load(self):
        """Load family tree from disk."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    data = json.load(f)
                    for member_data in data.get("members", []):
                        member = FamilyMember(**member_data)
                        self.members[member.id] = member
                    self.relationships = data.get("relationships", {})
            except Exception as e:
                print(f"⚠️  Failed to load family tree: {e}")
    
    def _save(self):
        """Save family tree to disk."""
        try:
            os.makedirs("memory", exist_ok=True)
            data = {
                "members": [m.to_dict() for m in self.members.values()],
                "relationships": self.relationships,
                "saved_at": datetime.now().isoformat()
            }
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save family tree: {e}")
    
    def add_member(self, member: FamilyMember) -> bool:
        """Add family member."""
        if member.id in self.members:
            print(f"⚠️  Member {member.id} already exists")
            return False
        
        self.members[member.id] = member
        self.relationships[member.id] = []
        self._save()
        return True
    
    def remove_member(self, member_id: str) -> bool:
        """Remove family member."""
        if member_id not in self.members:
            return False
        
        del self.members[member_id]
        if member_id in self.relationships:
            del self.relationships[member_id]
        
        # Remove from other relationships
        for rel_list in self.relationships.values():
            if member_id in rel_list:
                rel_list.remove(member_id)
        
        self._save()
        return True
    
    def get_member(self, member_id: str) -> Optional[FamilyMember]:
        """Retrieve family member."""
        return self.members.get(member_id)
    
    def record_visit(self, member_id: str) -> bool:
        """Record that family member visited."""
        if member_id not in self.members:
            return False
        
        member = self.members[member_id]
        now_iso = datetime.now().isoformat()
        member.visits.append(now_iso)
        member.last_visit = now_iso
        
        self._save()
        return True
    
    def get_all_members(self) -> List[FamilyMember]:
        """Get all family members."""
        return list(self.members.values())
    
    def get_overdue_members(self) -> List[FamilyMember]:
        """Get members who are overdue for a visit."""
        overdue = []
        for member in self.members.values():
            if member.is_overdue_for_visit():
                overdue.append(member)
        return sorted(overdue, key=lambda m: m.last_visit or "")
    
    def get_primary_caregiver(self) -> Optional[FamilyMember]:
        """Get primary caregiver (usually primary contact)."""
        caregivers = [m for m in self.members.values() if "caregiver" in m.relation.lower()]
        if caregivers:
            return caregivers[0]
        return None
    
    def get_member_summary(self, member_id: str) -> Optional[str]:
        """Get text summary of family member."""
        member = self.get_member(member_id)
        if not member:
            return None
        
        summary = f"{member.name} is your {member.relation}. "
        if member.bio:
            summary += member.bio + " "
        
        if member.last_visit:
            days_since = (datetime.now() - datetime.fromisoformat(member.last_visit)).days
            if days_since == 0:
                summary += "They visited today! "
            elif days_since == 1:
                summary += "They visited yesterday. "
            else:
                summary += f"They last visited {days_since} days ago. "
        
        return summary
    
    def get_daily_reminder_members(self) -> List[FamilyMember]:
        """Get family members with daily visit frequency."""
        return [m for m in self.members.values() if m.visit_frequency == "daily"]
    
    def create_greeting_message(self, member_id: str) -> str:
        """Create personalized greeting for family member."""
        member = self.get_member(member_id)
        if not member:
            return "Family member not found"
        
        greetings = [
            f"Hello! {member.name} is here to visit you.",
            f"Look who's here! It's {member.name}, your {member.relation}!",
            f"Great news! Your {member.relation} {member.name} has come to see you.",
            f"You have a visitor! It's {member.name}.",
        ]
        
        import random
        return random.choice(greetings)


class FamilyIntegration:
    """Integrate family management into main app."""
    
    def __init__(self, tts_engine=None):
        self.tree = FamilyTree()
        self.tts = tts_engine or pyttsx3.init()
    
    def announce_visitor(self, member_id: str):
        """Announce family member visit with voice."""
        message = self.tree.create_greeting_message(member_id)
        
        # Speak in friendly, clear voice
        self.tts.setProperty('rate', 120)
        self.tts.say(message)
        self.tts.runAndWait()
        
        # Record the visit
        self.tree.record_visit(member_id)
    
    def get_daily_family_messages(self) -> List[str]:
        """Get list of family members to mention today."""
        messages = []
        daily_members = self.tree.get_daily_reminder_members()
        
        for member in daily_members:
            summary = self.tree.get_member_summary(member.id)
            if summary:
                messages.append(summary)
        
        return messages
    
    def show_family_status(self) -> str:
        """Show overall family status."""
        members = self.tree.get_all_members()
        if not members:
            return "No family members registered"
        
        overdue = self.tree.get_overdue_members()
        summary = f"You have {len(members)} family members. "
        
        if overdue:
            summary += f"{len(overdue)} are overdue for a visit. "
        
        return summary
