import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import config

def get_db_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize database tables for conversations and messages."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                ON messages(conversation_id)
            """)
    finally:
        conn.close()

def create_conversation(title: Optional[str] = None) -> str:
    """Create a new conversation session and return its id."""
    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    if not title:
        title = "New Conversation"
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, title, now, now)
            )
        return conv_id
    finally:
        conn.close()

def get_conversations() -> List[Dict[str, Any]]:
    """Retrieve all conversations ordered by most recent update."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single conversation and its list of messages."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        conv = cursor.fetchone()
        if not conv:
            return None
        
        msg_cursor = conn.execute(
            "SELECT id, role, content, metadata, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,)
        )
        msg_rows = msg_cursor.fetchall()
        messages = []
        for row in msg_rows:
            item = dict(row)
            if item.get("metadata"):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except Exception:
                    pass
            messages.append(item)
            
        result = dict(conv)
        result["messages"] = messages
        return result
    finally:
        conn.close()

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Append a message to a conversation and update conversation timestamp."""
    now = datetime.now().isoformat()
    meta_json = json.dumps(metadata) if metadata else None
    
    conn = get_db_connection()
    try:
        with conn:
            # Ensure conversation exists
            cursor = conn.execute("SELECT id, title FROM conversations WHERE id = ?", (conversation_id,))
            conv = cursor.fetchone()
            if not conv:
                title = content[:30] + "..." if len(content) > 30 else content
                title = title.strip() or "Conversation"
                conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (conversation_id, title, now, now)
                )
            else:
                # If title is default and user sent first message, update title
                if conv["title"] == "New Conversation" and role == "user":
                    clean_title = content.replace("\n", " ").strip()
                    title = clean_title[:32] + ("..." if len(clean_title) > 32 else "")
                    conn.execute(
                        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                        (title, now, conversation_id)
                    )
                else:
                    conn.execute(
                        "UPDATE conversations SET updated_at = ? WHERE id = ?",
                        (now, conversation_id)
                    )

            cursor = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, role, content, meta_json, now)
            )
            return cursor.lastrowid
    finally:
        conn.close()

def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update conversation title."""
    now = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, conversation_id)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()

def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all its messages."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()

def clear_conversation_messages(conversation_id: str) -> bool:
    """Clear all messages in a conversation without deleting the conversation container."""
    now = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            return True
    finally:
        conn.close()
