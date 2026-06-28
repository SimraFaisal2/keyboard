"""
caregiver_dashboard.py — Local read-only Flask dashboard for caregivers.
Run standalone: python caregiver_dashboard.py
Or auto-started from MEMO mode on http://localhost:5050
"""

import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
_vault = None

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MEMO Caregiver Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1419; color: #e8eaed; padding: 2rem; }
    h1 { color: #7eb8ff; margin-bottom: 0.25rem; }
    .sub { color: #888; margin-bottom: 2rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
    .card { background: #1a2332; border: 1px solid #2a3a50; border-radius: 12px; padding: 1.25rem; }
    .card h2 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #7eb8ff; margin-bottom: 0.75rem; }
    .stat { font-size: 2rem; font-weight: 600; color: #80ffb0; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #2a3a50; }
    th { color: #888; }
    .pill { display: inline-block; background: #2a4060; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
    .med { background: #4a2040; color: #ffb0d0; }
    footer { margin-top: 2rem; color: #555; font-size: 0.8rem; }
  </style>
</head>
<body>
  <h1>MEMO Caregiver Dashboard</h1>
  <p class="sub">Local-only view · data never leaves this device</p>
  <div class="grid">
    <div class="card">
      <h2>Saved objects</h2>
      <div class="stat">{{ object_count }}</div>
    </div>
    <div class="card">
      <h2>Recalls (7 days)</h2>
      <div class="stat">{{ total_recalls }}</div>
    </div>
    <div class="card">
      <h2>User</h2>
      <div class="stat" style="font-size:1.4rem">{{ user_name }}</div>
    </div>
  </div>
  <div class="card" style="margin-top:1.5rem">
    <h2>Memory vault</h2>
    <table>
      <tr><th>Name</th><th>Note</th><th>Type</th><th>Recalls (7d)</th><th>Avg confidence</th></tr>
      {% for o in objects %}
      <tr>
        <td>{{ o.name }}</td>
        <td>{{ o.note or '—' }}</td>
        <td>{% if o.is_medication %}<span class="pill med">Medication</span>{% else %}<span class="pill">Object</span>{% endif %}</td>
        <td>{{ o.recall_count or 0 }}</td>
        <td>{% if o.avg_confidence %}{{ (o.avg_confidence * 100)|round(0)|int }}%{% else %}—{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <div class="card" style="margin-top:1.5rem">
    <h2>Recent recall activity</h2>
    <table>
      <tr><th>Time</th><th>Object</th><th>Confidence</th><th>Matched</th></tr>
      {% for r in recent %}
      <tr>
        <td>{{ r.timestamp[:19] }}</td>
        <td>{{ r.name or 'Unknown' }}</td>
        <td>{% if r.confidence %}{{ (r.confidence * 100)|round(0)|int }}%{% else %}—{% endif %}</td>
        <td>{{ 'Yes' if r.matched else 'No' }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <footer>Assistive cueing tool — not a medical device. For orientation support only.</footer>
</body>
</html>
"""


def init_vault(vault):
    global _vault
    _vault = vault


@app.route("/")
def index():
    if _vault is None:
        from memory.vault import MemoryVault
        init_vault(MemoryVault())
    stats = _vault.recall_stats(days=7)
    objects = _vault.list_objects()
    stat_map = {s["id"]: s for s in stats}
    merged = []
    for o in objects:
        s = stat_map.get(o["id"], {})
        merged.append({**o, **s})
    recent = _vault.recent_recalls(15)
    total_recalls = sum(s.get("recall_count") or 0 for s in stats)
    return render_template_string(
        DASHBOARD_HTML,
        object_count=len(objects),
        total_recalls=total_recalls,
        user_name=_vault.user_name,
        objects=merged,
        recent=recent,
    )


@app.route("/api/stats")
def api_stats():
    if _vault is None:
        return jsonify({"error": "vault not initialized"}), 503
    return jsonify({
        "objects": _vault.list_objects(),
        "recall_stats": _vault.recall_stats(7),
        "recent": _vault.recent_recalls(20),
    })


def run_dashboard(vault=None, port=5050, background=False):
    init_vault(vault)
    if background:
        import threading
        t = threading.Thread(
            target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
            daemon=True,
        )
        t.start()
        print(f"✅ Caregiver dashboard: http://127.0.0.1:{port}")
    else:
        print(f"Caregiver dashboard: http://127.0.0.1:{port}")
        app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    from memory.vault import MemoryVault
    run_dashboard(MemoryVault(), port=5050, background=False)
