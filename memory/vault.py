"""
memory/vault.py — SQLite storage for personal object memories.
Stores multiple embeddings per object (different angles), notes, voice clips, recall logs.
"""

import json
import os
import sqlite3
import datetime
import shutil
import zipfile
from typing import List, Optional, Tuple, Dict, Any

DEFAULT_DB = os.path.join("data", "memory", "vault.db")
THUMB_DIR = os.path.join("data", "memory", "thumbnails")
AUDIO_DIR = os.path.join("data", "memory", "audio")


class MemoryVault:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        os.makedirs(THUMB_DIR, exist_ok=True)
        os.makedirs(AUDIO_DIR, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self._conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                last_recalled_at TEXT,
                is_medication INTEGER DEFAULT 0,
                reminder_times TEXT DEFAULT '[]',
                voice_clip_path TEXT
            );
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER NOT NULL,
                vector BLOB NOT NULL,
                thumbnail_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS recall_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER,
                timestamp TEXT NOT NULL,
                confidence REAL,
                matched INTEGER DEFAULT 1,
                FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self._conn.commit()

    # ─── Settings ─────────────────────────────────────────────────────────────
    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()

    @property
    def user_name(self) -> str:
        return self.get_setting("user_name", "Friend")

    @user_name.setter
    def user_name(self, name: str):
        self.set_setting("user_name", name)

    # ─── Objects ──────────────────────────────────────────────────────────────
    def add_object(
        self,
        name: str,
        note: str = "",
        embeddings: Optional[List[Tuple[bytes, str]]] = None,
        is_medication: bool = False,
        reminder_times: Optional[List[str]] = None,
        voice_clip_path: Optional[str] = None,
    ) -> int:
        """Add object with one or more (vector_bytes, thumbnail_path) pairs."""
        now = datetime.datetime.now().isoformat()
        c = self._conn.cursor()
        c.execute(
            """INSERT INTO objects (name, note, created_at, is_medication,
               reminder_times, voice_clip_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name.strip(),
                note.strip(),
                now,
                int(is_medication),
                json.dumps(reminder_times or []),
                voice_clip_path,
            ),
        )
        obj_id = c.lastrowid
        for vec_bytes, thumb_path in (embeddings or []):
            c.execute(
                """INSERT INTO embeddings (object_id, vector, thumbnail_path, created_at)
                   VALUES (?, ?, ?, ?)""",
                (obj_id, vec_bytes, thumb_path, now),
            )
        self._conn.commit()
        return obj_id

    def add_embedding(self, object_id: int, vector_bytes: bytes, thumbnail_path: str):
        now = datetime.datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO embeddings (object_id, vector, thumbnail_path, created_at)
               VALUES (?, ?, ?, ?)""",
            (object_id, vector_bytes, thumbnail_path, now),
        )
        self._conn.commit()

    def list_objects(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT o.*, COUNT(e.id) AS embed_count
               FROM objects o LEFT JOIN embeddings e ON e.object_id = o.id
               GROUP BY o.id ORDER BY o.name"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_object(self, object_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM objects WHERE id=?", (object_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_embeddings(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT e.id AS embed_id, e.object_id, e.vector, e.thumbnail_path,
                      o.name, o.note, o.is_medication, o.voice_clip_path
               FROM embeddings e JOIN objects o ON o.id = e.object_id"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_thumbnails_for_object(self, object_id: int) -> List[str]:
        rows = self._conn.execute(
            "SELECT thumbnail_path FROM embeddings WHERE object_id=?",
            (object_id,),
        ).fetchall()
        return [r["thumbnail_path"] for r in rows if r["thumbnail_path"]]

    def update_last_recalled(self, object_id: int):
        now = datetime.datetime.now().isoformat()
        self._conn.execute(
            "UPDATE objects SET last_recalled_at=? WHERE id=?",
            (now, object_id),
        )
        self._conn.commit()

    def log_recall(
        self,
        object_id: Optional[int],
        confidence: float,
        matched: bool = True,
    ):
        now = datetime.datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO recall_log (object_id, timestamp, confidence, matched)
               VALUES (?, ?, ?, ?)""",
            (object_id, now, confidence, int(matched)),
        )
        self._conn.commit()
        if object_id and matched:
            self.update_last_recalled(object_id)

    def recall_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(days=days)
        ).isoformat()
        rows = self._conn.execute(
            """SELECT o.id, o.name,
                      COUNT(r.id) AS recall_count,
                      AVG(r.confidence) AS avg_confidence,
                      MAX(r.timestamp) AS last_recall
               FROM objects o
               LEFT JOIN recall_log r ON r.object_id = o.id AND r.timestamp >= ?
               GROUP BY o.id ORDER BY recall_count DESC""",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]

    def recent_recalls(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT r.*, o.name FROM recall_log r
               LEFT JOIN objects o ON o.id = r.object_id
               ORDER BY r.timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def medications_due_now(self, window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Return medication objects whose reminder time is within window."""
        now = datetime.datetime.now()
        current_hm = now.hour * 60 + now.minute
        due = []
        for obj in self.list_objects():
            if not obj["is_medication"]:
                continue
            times = json.loads(obj.get("reminder_times") or "[]")
            for t in times:
                try:
                    h, m = map(int, t.split(":"))
                    target = h * 60 + m
                    if abs(target - current_hm) <= window_minutes:
                        due.append(obj)
                        break
                except ValueError:
                    continue
        return due

    def save_thumbnail(self, image_bgr, prefix: str = "obj") -> str:
        import cv2
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(THUMB_DIR, f"{prefix}_{ts}.jpg")
        cv2.imwrite(path, image_bgr)
        return path

    def export_vault(self, zip_path: str):
        os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(self.db_path, "vault.db")
            for folder in (THUMB_DIR, AUDIO_DIR):
                if os.path.isdir(folder):
                    for root, _, files in os.walk(folder):
                        for f in files:
                            full = os.path.join(root, f)
                            zf.write(full, os.path.relpath(full, "data"))

    def import_vault(self, zip_path: str):
        extract_dir = os.path.join("data", "memory", "_import")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        imported_db = os.path.join(extract_dir, "vault.db")
        if os.path.exists(imported_db):
            self._conn.close()
            shutil.copy2(imported_db, self.db_path)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row

    def close(self):
        self._conn.close()
