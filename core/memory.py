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

            # Multi-turn conversation history with reasoning thoughts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    thought TEXT,
                    action_type TEXT,
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
        """Clears all stored memories and conversation turns."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memory")
            cursor.execute("DELETE FROM interaction_history")
            cursor.execute("DELETE FROM conversation_turns")
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

    # ── Multi-Turn Conversation Memory ──────────────────────────────────────────

    def log_turn(self, role: str, content: str, thought: Optional[str] = None, action_type: Optional[str] = None):
        """Records a single conversation turn from user or assistant with associated thought."""
        if not content or not content.strip():
            return
        with self._lock:
            now = datetime.now().isoformat()
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_turns (role, content, thought, action_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (role.lower(), content.strip(), thought.strip() if thought else None, action_type, now))
            conn.commit()
            conn.close()

    def get_recent_conversation(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent conversation turns in chronological order."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, role, content, thought, action_type, created_at
                FROM conversation_turns
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            turns = [
                {
                    "id": r[0],
                    "role": r[1],
                    "content": r[2],
                    "thought": r[3],
                    "action_type": r[4],
                    "created_at": r[5],
                }
                for r in reversed(rows)
            ]
            return turns

    def get_last_turn(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent turn, optionally filtered by role ('user' or 'assistant')."""
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            if role:
                cursor.execute("""
                    SELECT id, role, content, thought, action_type, created_at
                    FROM conversation_turns
                    WHERE role = ?
                    ORDER BY id DESC LIMIT 1
                """, (role.lower(),))
            else:
                cursor.execute("""
                    SELECT id, role, content, thought, action_type, created_at
                    FROM conversation_turns
                    ORDER BY id DESC LIMIT 1
                """)
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "thought": row[3],
                    "action_type": row[4],
                    "created_at": row[5],
                }
            return None

    def search_conversation_history(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches past conversation content for keywords."""
        if not query or not query.strip():
            return []
        tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        if not tokens:
            return []
        with self._lock:
            conn = sqlite3.connect(MEMORY_DB_FILE)
            cursor = conn.cursor()
            conditions = " OR ".join(["content LIKE ?" for _ in tokens])
            params = [f"%{tok}%" for tok in tokens]
            params.append(limit)
            cursor.execute(f"""
                SELECT id, role, content, thought, created_at
                FROM conversation_turns
                WHERE {conditions}
                ORDER BY id DESC LIMIT ?
            """, params)
            rows = cursor.fetchall()
            conn.close()
            return [
                {"id": r[0], "role": r[1], "content": r[2], "thought": r[3], "created_at": r[4]}
                for r in rows
            ]

    # ── User Facts & Personalization Memory ─────────────────────────────────────

    def store_fact(self, key: str, value: str, category: str = "user_fact"):
        """Stores a personalized user fact (e.g. 'favorite programming language', 'pet name')."""
        self.set_memory(category, key, value)

    def recall_fact(self, key: str) -> Optional[str]:
        """Recalls a user fact by key."""
        res = self.get_memory(key)
        return str(res) if res is not None else None

    def find_related_facts(self, query: str) -> List[Dict[str, Any]]:
        """Finds any stored user facts matching terms in the query."""
        all_mem = self.list_all_memories()
        q_lower = query.lower()
        matches = []
        for m in all_mem:
            k = m["key"].lower()
            v = str(m["value"]).lower()
            if k in q_lower or any(word in q_lower for word in k.split() if len(word) > 3):
                matches.append(m)
        return matches
