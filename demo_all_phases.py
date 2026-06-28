#!/usr/bin/env python
"""
demo_all_phases.py — Comprehensive demo of all phases (1-5).
Run this to see the complete dementia memory system in action.
"""

import sys
sys.path.insert(0, '.')

from memory.object_model import EnhancedMemoryVault, PersonalObject
from memory.teach_module import TeachSession
from memory.reminders import RoutineReminder, VoiceCue, ReminderType
from memory.comfort_mode import ComfortMode, SpatialMemory
from memory.family_relations import FamilyTree, FamilyMember
from memory.phase5_ux import DementiaUX
from datetime import datetime, timedelta
import time


def demo_phase_1():
    """Demo: Core Memory System"""
    print("\n" + "="*70)
    print("PHASE 1: CORE MEMORY SYSTEM")
    print("="*70)
    
    vault = EnhancedMemoryVault()
    
    # Create test objects
    objects = [
        PersonalObject(
            id="wedding_ring",
            name="Wedding Ring",
            category="personal",
            importance=5,
            location="left nightstand drawer",
            description="Gold wedding ring with diamond from grandmother"
        ),
        PersonalObject(
            id="house_keys",
            name="House Keys",
            category="essentials",
            importance=4,
            location="hallway key rack",
            description="Silver house keys with blue keychain"
        ),
        PersonalObject(
            id="reading_glasses",
            name="Reading Glasses",
            category="medical",
            importance=4,
            location="living room side table",
            description="Prescription reading glasses in brown case"
        ),
    ]
    
    # Save objects
    print("\n📝 Teaching system about personal objects:")
    for obj in objects:
        vault.add_object(obj)
        print(f"  ✅ Learned: {obj.name}")
        print(f"     Location: {obj.location}")
        print(f"     Importance: {obj.importance}/5")
    
    # Retrieve and display
    print("\n🔍 Retrieving objects from vault:")
    all_objects = vault.list_objects()
    for obj in all_objects:
        print(f"  • {obj.name} ({obj.category}) - {obj.location}")
    
    # Mark detection
    print("\n📍 Simulating object detection:")
    vault.mark_detected("wedding_ring", "bedroom")
    obj = vault.get_object("wedding_ring")
    print(f"  ✅ {obj.name} last seen at: {obj.last_seen_location}")
    print(f"     Detection count: {obj.detection_count}")


def demo_phase_2():
    """Demo: Smart Reminders"""
    print("\n" + "="*70)
    print("PHASE 2: SMART REMINDERS")
    print("="*70)
    
    vault = EnhancedMemoryVault()
    reminders = RoutineReminder(vault)
    
    # Show configured routines
    print("\n⏰ Configured daily routines:")
    for reminder_type, routine in reminders.routines.items():
        status = "✅ ENABLED" if routine['enabled'] else "❌ DISABLED"
        print(f"  {reminder_type.value.upper():12} at {routine['time'][0]:02d}:{routine['time'][1]:02d} - {status}")
        print(f"    Prompts: {routine['prompts'][0][:50]}...")
    
    # Show activity log
    print("\n📋 Activity log:")
    reminders.log_activity("demo_event", {"details": "Demonstration log entry"})
    activity = reminders.get_activity_log(hours=24)
    print(f"  Recent events: {len(activity)}")
    for event in activity[-3:]:
        print(f"    • {event['event']} at {event['timestamp']}")
    
    # Export report
    print("\n📊 Exporting activity report:")
    reminders.export_activity_report()
    print("  ✅ Report saved to: memory/activity_report.json")


def demo_phase_4_comfort():
    """Demo: Emotional Comfort Mode"""
    print("\n" + "="*70)
    print("PHASE 4A: EMOTIONAL COMFORT MODE")
    print("="*70)
    
    comfort = ComfortMode()
    
    # Add family members
    comfort.add_family_member(
        name="Sarah",
        relation="daughter",
        voice_path="memory/family_voices/sarah.wav"
    )
    comfort.add_family_member(
        name="John",
        relation="grandson",
        voice_path="memory/family_voices/john.wav"
    )
    
    print("\n👥 Family members registered for comfort:")
    for name, info in comfort.family_relations.items():
        print(f"  • {name} ({info['relation']})")
    
    # Get introductions
    print("\n💬 Family introductions:")
    intro = comfort.get_family_introduction("Sarah")
    print(f"  {intro}")


def demo_phase_4_spatial():
    """Demo: Spatial Memory"""
    print("\n" + "="*70)
    print("PHASE 4B: SPATIAL MEMORY")
    print("="*70)
    
    spatial = SpatialMemory()
    
    # Add rooms
    spatial.add_room("bedroom", "Main sleeping area")
    spatial.add_room("living room", "Main gathering area")
    spatial.add_room("kitchen", "Cooking area")
    
    print("\n🏠 Rooms registered:")
    for room_name in spatial.rooms.keys():
        print(f"  • {room_name}")
    
    # Set bedroom as current
    spatial.set_current_room("bedroom")
    
    # Add object zones
    spatial.add_object_zone("bedroom", "wedding_ring", 100, 50, 150, 100)
    spatial.add_object_zone("bedroom", "reading_glasses", 200, 80, 250, 130)
    spatial.add_object_zone("living room", "house_keys", 50, 100, 100, 150)
    
    print("\n📍 Object locations (spatial zones):")
    for room_name in ["bedroom", "living room"]:
        spatial.set_current_room(room_name)
        summary = spatial.get_room_summary()
        print(f"  {room_name}: {summary}")
        
        # Query specific locations
        desc = spatial.where_is_object("wedding_ring", room_name)
        if desc:
            print(f"    → {desc}")


def demo_phase_4_family():
    """Demo: Family Tree Management"""
    print("\n" + "="*70)
    print("PHASE 4C: FAMILY TREE MANAGEMENT")
    print("="*70)
    
    tree = FamilyTree()
    
    # Add family members
    members = [
        FamilyMember(
            id="daughter_sarah",
            name="Sarah",
            relation="daughter",
            phone="555-0001",
            email="sarah@email.com",
            bio="Lives nearby, visits weekly",
            visit_frequency="weekly"
        ),
        FamilyMember(
            id="grandson_john",
            name="John",
            relation="grandson",
            phone="555-0002",
            email="john@email.com",
            bio="Visits on weekends",
            visit_frequency="bi-weekly"
        ),
        FamilyMember(
            id="caregiver_maria",
            name="Maria",
            relation="caregiver",
            phone="555-0003",
            email="maria@email.com",
            bio="Full-time caregiver",
            visit_frequency="daily"
        ),
    ]
    
    print("\n👨‍👩‍👧 Adding family members:")
    for member in members:
        tree.add_member(member)
        print(f"  ✅ {member.name} ({member.relation}) - {member.visit_frequency} visits")
    
    # Record some visits
    print("\n📅 Recording visits:")
    tree.record_visit("daughter_sarah")
    print(f"  ✅ Recorded visit from Sarah")
    
    # Get overdue
    print("\n⚠️ Visit status:")
    all_members = tree.get_all_members()
    print(f"  Total family members: {len(all_members)}")
    overdue = tree.get_overdue_members()
    print(f"  Overdue for visit: {len(overdue)}")
    for member in overdue:
        print(f"    • {member.name} (last: {member.last_visit})")
    
    # Get daily reminders
    print("\n📍 Daily family reminders:")
    daily = tree.get_daily_reminder_members()
    for member in daily:
        print(f"  • {member.name} should visit today")


def demo_phase_5():
    """Demo: Dementia UX Principles"""
    print("\n" + "="*70)
    print("PHASE 5: DEMENTIA-FRIENDLY UX PRINCIPLES")
    print("="*70)
    
    ux = DementiaUX()
    
    print("\n🎨 UX Component Specifications:")
    principles = ux.get_dementia_ux_principles()
    for principle, description in principles.items():
        print(f"  • {principle:20} → {description}")
    
    print("\n🔧 Available UX Components:")
    components = [
        "draw_large_button()",
        "draw_simple_menu()",
        "show_validation_feedback()",
        "show_progress_indicator()",
        "draw_action_instructions()",
        "draw_calm_frame()",
    ]
    for component in components:
        print(f"  ✅ {component}")


def demo_integration():
    """Demo: Integrated MEMO Mode"""
    print("\n" + "="*70)
    print("INTEGRATED: MEMO MODE (ALL PHASES)")
    print("="*70)
    
    from memo_mode_integrated import MemoSession, MemoState
    
    memo = MemoSession()
    
    print("\n🎯 MEMO Mode States:")
    states = list(MemoState)
    for idx, state in enumerate(states, 1):
        print(f"  {idx}. {state.value.upper():12} → {state.name}")
    
    print("\n📋 MEMO Menu Options:")
    options = memo.get_menu_options()
    for idx, option in enumerate(options, 1):
        print(f"  {idx}. {option}")
    
    print("\n✨ Integration Features:")
    features = [
        "Phase 1: Teach objects with calm guidance",
        "Phase 2: Time-based routine reminders",
        "Phase 3: Real-time caregiver dashboard",
        "Phase 4: Emotional support & family connections",
        "Phase 5: Dementia-friendly UI throughout",
    ]
    for feature in features:
        print(f"  ✅ {feature}")


def main():
    """Run all demos"""
    print("\n" + "🎉 "*35)
    print("COMPLETE DEMENTIA MEMORY SYSTEM - ALL PHASES DEMO")
    print("🎉 "*35)
    
    try:
        demo_phase_1()
        demo_phase_2()
        demo_phase_4_comfort()
        demo_phase_4_spatial()
        demo_phase_4_family()
        demo_phase_5()
        demo_integration()
        
        print("\n" + "="*70)
        print("✅ ALL PHASES DEMONSTRATED SUCCESSFULLY!")
        print("="*70)
        print("\n📚 Next Steps:")
        print("  1. Run: python index.py")
        print("  2. Test pinch-to-ASL in GRID mode")
        print("  3. Cycle to MEMO mode")
        print("  4. In another terminal: python caregiver_web.py")
        print("  5. Open browser: http://localhost:5000")
        print("\n📖 Documentation:")
        print("  • ALL_PHASES_COMPLETE.md - Full system overview")
        print("  • DEMENTIA_MEMORY_PLAN.md - 8-week roadmap")
        print("  • memory/*.py - Individual module docs")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
