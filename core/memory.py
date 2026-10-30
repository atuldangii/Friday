"""
Memory and Personalization Engine for FRIDAY AI.
Stores facts, preferences, and action history in a local SQLite database.
"""

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.constants import MEMORY_DB_FILE


class MemoryManager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoryManager, cls).__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            
            # Key-Value preferences and user facts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Frequent command / interaction history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interaction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    action_taken TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.commit()
            conn.close()

    def set_memory(self, category: str, key: str, value: Any):
        """Saves or updates a memory item."""
        with self._lock:
            val_str = json.dumps(value) if not isinstance(value, str) else value
            now = datetime.now().isoformat()
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memory (category, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    category=excluded.category,
                    value=excluded.value,
                    updated_at=excluded.updated_at
            """, (category, key.strip().lower(), val_str, now))
            conn.commit()
            conn.close()

    def get_memory(self, key: str, default: Any = None) -> Any:
        """Retrieves a memory item by key."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_memory WHERE key = ?", (key.strip().lower(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return default

    def delete_memory(self, key: str) -> bool:
        """Deletes a specific memory item."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memory WHERE key = ?", (key.strip().lower(),))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted

    def list_all_memories(self) -> List[Dict[str, Any]]:
        """Returns all stored user memories."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, category, key, value, updated_at FROM user_memory ORDER BY category, key")
            rows = cursor.fetchall()
            conn.close()
            return [
                {"id": r[0], "category": r[1], "key": r[2], "value": r[3], "updated_at": r[4]}
                for r in rows
            ]

    def clear_all(self):
        """Clears all stored memories."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memory")
            cursor.execute("DELETE FROM interaction_history")
            conn.commit()
            conn.close()

    def log_interaction(self, command: str, action_taken: str):
        with self._lock:
            now = datetime.now().isoformat()
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interaction_history (command, action_taken, created_at)
                VALUES (?, ?, ?)
            """, (command, action_taken, now))
            conn.commit()
            conn.close()

    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, str]]:
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT command, action_taken, created_at FROM interaction_history ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [{"command": r[0], "action_taken": r[1], "created_at": r[2]} for r in rows]
