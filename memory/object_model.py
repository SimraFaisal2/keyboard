"""
object_model.py — Enhanced personal object storage for dementia memory system.
Phase 1: Object teaching, recognition, location tagging, voice context.
"""

import os
import sqlite3
import numpy as np
import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json

# ─── Object Data Structure ────────────────────────────────────────────────────
@dataclass
class PersonalObject:
    """Represents one personal object with full context."""
    id: str                        # unique ID (uuid or hash)
    name: str                      # "wedding ring", "left shoe"
    category: str                  # 'medical', 'personal', 'family', 'clothing', 'keys'
    importance: int                # 1-5 (5=medication, 4=keys, 3=glasses, 2=other, 1=misc)
    location: str                  # "left nightstand drawer" or "bedroom"
    
    # Media
    photo_paths: List[str] = field(default_factory=list)  # reference images (3+)
    embeddings: Optional[np.ndarray] = None                # feature vectors
    voice_path: Optional[str] = None                       # audio description
    
    # Context & relationships
    description: str = ""          # "wedding ring from grandmother"
    related_objects: List[str] = field(default_factory=list)  # IDs of related items
    routines: List[str] = field(default_factory=list)     # ['morning', 'bedtime']
    
    # Metadata
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    last_seen: Optional[datetime.datetime] = None
    last_seen_location: Optional[str] = None
    detection_count: int = 0       # how many times detected
    
    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'importance': self.importance,
            'location': self.location,
            'photo_paths': self.photo_paths,
            'voice_path': self.voice_path,
            'description': self.description,
            'related_objects': self.related_objects,
            'routines': self.routines,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_seen_location': self.last_seen_location,
            'detection_count': self.detection_count,
        }


# ─── Enhanced Vault with Phase 1 Features ─────────────────────────────────────
class EnhancedMemoryVault:
    """
    Phase 1: Object storage with location tagging, importance levels, voice context.
    Stores in: /memory/objects/ (photos + voice) and objects.db (metadata)
    """
    
    def __init__(self, base_path: str = "memory"):
        self.base_path = base_path
        self.user_name = "User"
        self.objects_dir = os.path.join(base_path, "objects")
        self.photos_dir = os.path.join(self.objects_dir, "photos")
        self.voices_dir = os.path.join(self.objects_dir, "voices")
        self.db_path = os.path.join(base_path, "objects.db")
        
        # Create directories
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.voices_dir, exist_ok=True)
        
        # Initialize database
        self._init_db()
        self.objects: Dict[str, PersonalObject] = {}
        self._load_all()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS objects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            importance INTEGER,
            location TEXT,
            description TEXT,
            voice_path TEXT,
            created_at TIMESTAMP,
            last_seen TIMESTAMP,
            last_seen_location TEXT,
            detection_count INTEGER DEFAULT 0
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS object_photos (
            id TEXT,
            photo_path TEXT,
            order_idx INTEGER,
            PRIMARY KEY (id, photo_path),
            FOREIGN KEY (id) REFERENCES objects(id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS relationships (
            object_id TEXT,
            related_id TEXT,
            relation_type TEXT,
            PRIMARY KEY (object_id, related_id),
            FOREIGN KEY (object_id) REFERENCES objects(id),
            FOREIGN KEY (related_id) REFERENCES objects(id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS routines (
            object_id TEXT,
            routine_type TEXT,
            PRIMARY KEY (object_id, routine_type),
            FOREIGN KEY (object_id) REFERENCES objects(id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS object_embeddings (
            id TEXT,
            object_id TEXT,
            vector BLOB,
            thumbnail_path TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY (object_id) REFERENCES objects(id)
        )''')
        
        conn.commit()
        conn.close()
    
    def add_object(self, obj: Optional[PersonalObject] = None, name=None, note=None, embeddings=None, is_medication=False, reminder_times=None, voice_clip_path=None) -> bool:
        """Add or update an object in the vault."""
        if obj is None:
            import uuid
            obj = PersonalObject(
                id=str(uuid.uuid4()),
                name=name or "Unknown",
                category="medical" if is_medication else "general",
                importance=5 if is_medication else 2,
                location="unknown",
                description=note or "",
                voice_path=voice_clip_path,
                routines=["morning", "evening"] if is_medication else [],
                photo_paths=[thumb for (vec, thumb) in (embeddings or [])]
            )
            obj._raw_embeddings = embeddings
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''INSERT OR REPLACE INTO objects
                (id, name, category, importance, location, description, 
                 voice_path, created_at, last_seen, last_seen_location, detection_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (obj.id, obj.name, obj.category, obj.importance, obj.location,
                 obj.description, obj.voice_path, obj.created_at, obj.last_seen,
                 obj.last_seen_location, obj.detection_count))
            
            # Store photo paths
            for idx, photo_path in enumerate(obj.photo_paths):
                c.execute('''INSERT OR REPLACE INTO object_photos 
                    (id, photo_path, order_idx) VALUES (?, ?, ?)''',
                    (obj.id, photo_path, idx))
            
            # Store relationships
            for related_id in obj.related_objects:
                c.execute('''INSERT OR IGNORE INTO relationships
                    (object_id, related_id, relation_type) VALUES (?, ?, ?)''',
                    (obj.id, related_id, 'related'))
            
            # Store routines
            for routine in obj.routines:
                c.execute('''INSERT OR IGNORE INTO routines
                    (object_id, routine_type) VALUES (?, ?)''',
                    (obj.id, routine))
                    
            if hasattr(obj, '_raw_embeddings') and obj._raw_embeddings:
                import uuid
                for vec_bytes, thumb_path in obj._raw_embeddings:
                    c.execute('''INSERT INTO object_embeddings (id, object_id, vector, thumbnail_path) VALUES (?, ?, ?, ?)''',
                              (str(uuid.uuid4()), obj.id, vec_bytes, thumb_path))
            
            conn.commit()
            conn.close()
            
            self.objects[obj.id] = obj
            return True
        except Exception as e:
            print(f"❌ Error saving object {obj.id}: {e}")
            return False
    
    def get_object(self, obj_id: str) -> Optional[PersonalObject]:
        """Retrieve object by ID."""
        if obj_id in self.objects:
            return self.objects[obj_id]
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT * FROM objects WHERE id=?', (obj_id,))
            row = c.fetchone()
            if not row:
                conn.close()
                return None
            
            obj = PersonalObject(
                id=row[0], name=row[1], category=row[2],
                importance=row[3], location=row[4],
                description=row[5], voice_path=row[6],
                created_at=datetime.datetime.fromisoformat(row[7]),
                last_seen=datetime.datetime.fromisoformat(row[8]) if row[8] else None,
                last_seen_location=row[9],
                detection_count=row[10]
            )
            
            # Load photos
            c.execute('SELECT photo_path FROM object_photos WHERE id=? ORDER BY order_idx',
                     (obj_id,))
            obj.photo_paths = [p[0] for p in c.fetchall()]
            
            # Load relationships
            c.execute('SELECT related_id FROM relationships WHERE object_id=?', (obj_id,))
            obj.related_objects = [r[0] for r in c.fetchall()]
            
            # Load routines
            c.execute('SELECT routine_type FROM routines WHERE object_id=?', (obj_id,))
            obj.routines = [r[0] for r in c.fetchall()]
            
            conn.close()
            return obj
        except Exception as e:
            print(f"❌ Error loading object {obj_id}: {e}")
            return None
    
    def list_objects(self, category: Optional[str] = None) -> List[PersonalObject]:
        """List all objects, optionally filtered by category."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            if category:
                c.execute('SELECT id FROM objects WHERE category=?', (category,))
            else:
                c.execute('SELECT id FROM objects')
            
            obj_ids = [row[0] for row in c.fetchall()]
            conn.close()
            
            return [self.get_object(oid) for oid in obj_ids if oid]
        except Exception as e:
            print(f"❌ Error listing objects: {e}")
            return []
    
    def mark_detected(self, obj_id: str, location: Optional[str] = None) -> bool:
        """Update last_seen timestamp and location when object is detected."""
        try:
            obj = self.get_object(obj_id)
            if not obj:
                return False
            
            obj.last_seen = datetime.datetime.now()
            if location:
                obj.last_seen_location = location
            obj.detection_count += 1
            
            return self.add_object(obj)
        except Exception as e:
            print(f"❌ Error marking detected: {e}")
            return False
    
    def _load_all(self):
        """Load all objects from database on startup."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT id FROM objects')
            obj_ids = [row[0] for row in c.fetchall()]
            conn.close()
            
            for obj_id in obj_ids:
                obj = self.get_object(obj_id)
                if obj:
                    self.objects[obj_id] = obj
            
            if obj_ids:
                print(f"✅ Loaded {len(obj_ids)} objects from vault")
        except Exception as e:
            print(f"⚠️  Error loading vault: {e}")
    
    def medications_due_now(self) -> List[dict]:
        due = []
        for obj in self.objects.values():
            if obj.importance == 5 or obj.category == 'medical':
                due.append({
                    "id": obj.id,
                    "name": obj.name,
                    "note": obj.description
                })
        return due

    def save_thumbnail(self, crop, prefix="thumb") -> str:
        import cv2
        import uuid
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
        path = os.path.join(self.photos_dir, filename)
        cv2.imwrite(path, crop)
        return path

    def get_all_embeddings(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT e.id, e.object_id, e.vector, e.thumbnail_path, o.name, o.description, o.voice_path, o.category FROM object_embeddings e JOIN objects o ON e.object_id = o.id')
        rows = c.fetchall()
        conn.close()
        catalog = []
        for row in rows:
            catalog.append({
                "embed_id": row[0],
                "object_id": row[1],
                "vector": row[2],
                "thumbnail_path": row[3],
                "name": row[4],
                "note": row[5],
                "voice_clip_path": row[6],
                "is_medication": (row[7] == 'medical')
            })
        return catalog

    def get_thumbnails_for_object(self, obj_id: str) -> List[str]:
        obj = self.get_object(obj_id)
        if obj:
            return obj.photo_paths
        return []

    def export_summary(self) -> Dict:
        """Export all objects as JSON summary for caregiver."""
        return {
            'total_objects': len(self.objects),
            'objects': [obj.to_dict() for obj in self.objects.values()],
            'export_time': datetime.datetime.now().isoformat(),
        }
