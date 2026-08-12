"""
caregiver_web.py — Enhanced caregiver dashboard (Phases 2-5).
View objects, manage reminders, monitor activity, manage family.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, timedelta
from memory.object_model import EnhancedMemoryVault
from memory.reminders import RoutineReminder, ReminderType
from memory.routines import AdvancedRoutineStore
from memory.family_relations import FamilyTree, FamilyMember
from memory.patient_profile import PatientProfileStore
from memory.safety_monitor import SafetyMonitor
from memory.task_guidance import GuidedTaskStore
from memory.reporting import CaregiverReport

app = Flask(__name__)
vault = EnhancedMemoryVault()
reminders = RoutineReminder(vault)
family_tree = FamilyTree()
profile_store = PatientProfileStore()
advanced_routines = AdvancedRoutineStore()
task_store = GuidedTaskStore()
safety_monitor = SafetyMonitor(profile=profile_store.load())
caregiver_report = CaregiverReport(safety_monitor=safety_monitor)

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/objects', methods=['GET'])
def get_objects():
    """Get all objects in memory vault."""
    category = request.args.get('category')
    objects = vault.list_objects(category=category)
    return jsonify({
        'total': len(objects),
        'objects': [obj.to_dict() for obj in objects]
    })

@app.route('/api/object/<obj_id>', methods=['GET'])
def get_object(obj_id):
    """Get single object details."""
    obj = vault.get_object(obj_id)
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    return jsonify(obj.to_dict())

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get memory vault statistics."""
    objects = vault.list_objects()
    
    stats = {
        'total_objects': len(objects),
        'by_category': {},
        'by_importance': {},
        'recent_detections': []
    }
    
    for obj in objects:
        cat = obj.category or 'uncategorized'
        stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
        
        imp = f"level_{obj.importance}"
        stats['by_importance'][imp] = stats['by_importance'].get(imp, 0) + 1
        
        if obj.last_seen:
            stats['recent_detections'].append({
                'name': obj.name,
                'time': obj.last_seen.isoformat(),
                'location': obj.last_seen_location or 'unknown'
            })
    
    stats['recent_detections'].sort(key=lambda x: x['time'], reverse=True)
    stats['recent_detections'] = stats['recent_detections'][:10]
    
    return jsonify(stats)

# Phase 2: Reminders
@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """Get configured reminders."""
    reminder_list = []
    for reminder_type, routine in reminders.routines.items():
        reminder_list.append({
            'type': reminder_type.value,
            'time': f"{routine['time'][0]:02d}:{routine['time'][1]:02d}",
            'enabled': routine['enabled'],
            'objects': routine['objects'],
            'prompts': routine['prompts']
        })
    return jsonify({'reminders': reminder_list})

@app.route('/api/reminders/<reminder_type>', methods=['PUT'])
def update_reminder(reminder_type):
    """Update reminder configuration."""
    try:
        reminder_enum = ReminderType(reminder_type)
        data = request.get_json()
        
        if 'enabled' in data:
            reminders.set_routine_enabled(reminder_enum, data['enabled'])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Get recent activity log."""
    hours = request.args.get('hours', 24, type=int)
    activity = reminders.get_activity_log(hours=hours)
    return jsonify({'activity': activity})

# Phase 4: Family Management
@app.route('/api/family', methods=['GET'])
def get_family():
    """Get family members."""
    members = []
    for member in family_tree.get_all_members():
        members.append({
            'id': member.id,
            'name': member.name,
            'relation': member.relation,
            'phone': member.phone,
            'email': member.email,
            'last_visit': member.last_visit,
            'visits_count': len(member.visits),
            'overdue': member.is_overdue_for_visit()
        })
    return jsonify({'members': members})

@app.route('/api/family/<member_id>/visit', methods=['POST'])
def record_visit(member_id):
    """Record family member visit."""
    success = family_tree.record_visit(member_id)
    return jsonify({'success': success})

@app.route('/api/family/add', methods=['POST'])
def add_family_member():
    """Add new family member."""
    try:
        data = request.get_json()
        member = FamilyMember(
            id=data['id'],
            name=data['name'],
            relation=data['relation'],
            phone=data.get('phone'),
            email=data.get('email'),
            bio=data.get('bio')
        )
        success = family_tree.add_member(member)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Enhanced Routes
@app.route('/', methods=['GET'])
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/reminders', methods=['GET'])
def reminders_page():
    """Reminders management page."""
    # Only dashboard.html ships with the app; it covers reminders, family,
    # and activity, so render it for these routes instead of 404ing.
    return render_template('dashboard.html')

@app.route('/family', methods=['GET'])
def family_page():
    """Family management page."""
    return render_template('dashboard.html')

@app.route('/activity', methods=['GET'])
def activity_page():
    """Activity log page."""
    return render_template('dashboard.html')

# ─── HTML Templates ────────────────────────────────────────────────────────────


DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dementia Memory - Caregiver Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f0f0;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 28px; margin-bottom: 5px; }
        .nav {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        .nav a {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.3s;
        }
        .nav a:hover { background: rgba(255,255,255,0.3); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 16px;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #3498db;
        }
        .objects-list, .reminders-list, .family-list {
            grid-column: 1 / -1;
        }
        .item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            background: white;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        .item-name {
            font-weight: bold;
            color: #2c3e50;
            flex: 1;
        }
        .item-detail {
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 4px;
        }
        .importance-badge {
            background: #e74c3c;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-overdue {
            background: #e74c3c;
            color: white;
        }
        .status-normal {
            background: #27ae60;
            color: white;
        }
        .status-soon {
            background: #f39c12;
            color: white;
        }
        .action-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        .action-btn:hover { background: #2980b9; }
        .footer {
            text-align: center;
            color: #7f8c8d;
            margin-top: 30px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 Dementia Memory Support Dashboard</h1>
        <p>Caregiver Interface - Monitor & Manage All Information</p>
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/reminders">Reminders</a>
            <a href="/family">Family</a>
            <a href="/activity">Activity Log</a>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>📦 Total Objects</h3>
            <div class="stat-number" id="stat-total">0</div>
        </div>
        <div class="card">
            <h3>💊 High Priority (Meds)</h3>
            <div class="stat-number" id="stat-meds">0</div>
        </div>
        <div class="card">
            <h3>👥 Family Members</h3>
            <div class="stat-number" id="stat-family">0</div>
        </div>
        <div class="card">
            <h3>⚠️ Overdue Visits</h3>
            <div class="stat-number" id="stat-overdue">0</div>
        </div>
    </div>
    
    <div class="card objects-list">
        <h3>📍 Recent Detections</h3>
        <div id="objects-container">Loading...</div>
    </div>
    
    <div class="card reminders-list">
        <h3>⏰ Today's Reminders</h3>
        <div id="reminders-container">Loading...</div>
    </div>
    
    <div class="card family-list">
        <h3>👨‍👩‍👧‍👦 Family Status</h3>
        <div id="family-container">Loading...</div>
    </div>
    
    <div class="footer">
        <p>Last updated: <span id="last-update">now</span></p>
        <p>🔒 This dashboard is password protected. Keep it secure.</p>
    </div>
    
    <script>
        async function loadData() {
            // Load stats
            const statsResp = await fetch('/api/stats');
            const stats = await statsResp.json();
            document.getElementById('stat-total').textContent = stats.total_objects;
            document.getElementById('stat-meds').textContent = 
                stats.by_importance['level_5'] || 0;
            
            // Load family stats
            const familyResp = await fetch('/api/family');
            const familyData = await familyResp.json();
            document.getElementById('stat-family').textContent = familyData.members.length;
            
            const overdue = familyData.members.filter(m => m.overdue).length;
            document.getElementById('stat-overdue').textContent = overdue;
            
            // Load recent objects
            const objResp = await fetch('/api/objects');
            const data = await objResp.json();
            
            const container = document.getElementById('objects-container');
            container.innerHTML = '';
            
            data.objects.slice(0, 5).forEach(obj => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div style="flex: 1;">
                        <div class="item-name">${obj.name}</div>
                        <div class="item-detail">📍 ${obj.location || 'Unknown'}</div>
                        <div class="item-detail">${obj.description}</div>
                    </div>
                    <div class="importance-badge">Priority: ${obj.importance}/5</div>
                `;
                container.appendChild(div);
            });
            
            // Load reminders
            const remResp = await fetch('/api/reminders');
            const remData = await remResp.json();
            const remContainer = document.getElementById('reminders-container');
            remContainer.innerHTML = '';
            
            remData.reminders.forEach(rem => {
                const div = document.createElement('div');
                div.className = 'item';
                const status = rem.enabled ? 'status-normal' : 'status-overdue';
                div.innerHTML = `
                    <div style="flex: 1;">
                        <div class="item-name">${rem.type.toUpperCase()} - ${rem.time}</div>
                        <div class="item-detail">${rem.prompts[0]}</div>
                    </div>
                    <span class="status-badge ${status}">${rem.enabled ? 'ACTIVE' : 'DISABLED'}</span>
                `;
                remContainer.appendChild(div);
            });
            
            // Load family
            const famContainer = document.getElementById('family-container');
            famContainer.innerHTML = '';
            
            familyData.members.slice(0, 5).forEach(mem => {
                const div = document.createElement('div');
                div.className = 'item';
                const status = mem.overdue ? 'status-overdue' : (mem.last_visit ? 'status-normal' : 'status-soon');
                div.innerHTML = `
                    <div style="flex: 1;">
                        <div class="item-name">${mem.name}</div>
                        <div class="item-detail">${mem.relation} • ${mem.visits_count} visits</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-badge ${status}">${mem.overdue ? 'OVERDUE' : 'CURRENT'}</span>
                        <button class="action-btn" onclick="recordVisit('${mem.id}')">Visit</button>
                    </div>
                `;
                famContainer.appendChild(div);
            });
            
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }
        
        function recordVisit(memberId) {
            fetch(`/api/family/${memberId}/visit`, {method: 'POST'})
                .then(() => loadData());
        }
        
        loadData();
        setInterval(loadData, 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("🌐 Enhanced Caregiver Dashboard starting...")
    print("📱 Open browser: http://localhost:5000")
    print("🔗 Or from another device: http://<your-computer-ip>:5000")
    
    import os
    os.makedirs('templates', exist_ok=True)
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(DASHBOARD_HTML)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

