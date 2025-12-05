import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config import MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize the database tables."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create chats table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER PRIMARY KEY,
                        custom_role TEXT,
                        custom_goal TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Try to add timeout_seconds column if it doesn't exist
                try:
                    cursor.execute("ALTER TABLE chats ADD COLUMN timeout_seconds INTEGER DEFAULT NULL")
                except sqlite3.OperationalError:
                    # Column likely already exists
                    pass
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully.")
                
            # Perform cleanup on startup
            self.cleanup_old_messages()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_chat_settings(self, chat_id: int) -> Dict[str, str]:
        """Retrieve custom role, goal, and timeout for a chat."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT custom_role, custom_goal, timeout_seconds FROM chats WHERE chat_id = ?", (chat_id,))
                row = cursor.fetchone()
                if row:
                    return {"custom_role": row[0], "custom_goal": row[1], "timeout_seconds": row[2]}
                return {"custom_role": "", "custom_goal": "", "timeout_seconds": None}
        except Exception as e:
            logger.error(f"Error getting chat settings for {chat_id}: {e}")
            return {"custom_role": "", "custom_goal": "", "timeout_seconds": None}

    def update_chat_settings(self, chat_id: int, custom_role: Optional[str] = None, custom_goal: Optional[str] = None, timeout_seconds: Optional[int] = None):
        """Update or insert chat settings."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if chat exists
                cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
                exists = cursor.fetchone()
                
                if exists:
                    if custom_role is not None:
                        cursor.execute("UPDATE chats SET custom_role = ? WHERE chat_id = ?", (custom_role, chat_id))
                    if custom_goal is not None:
                        cursor.execute("UPDATE chats SET custom_goal = ? WHERE chat_id = ?", (custom_goal, chat_id))
                    if timeout_seconds is not None:
                        cursor.execute("UPDATE chats SET timeout_seconds = ? WHERE chat_id = ?", (timeout_seconds, chat_id))
                else:
                    role = custom_role if custom_role is not None else ""
                    goal = custom_goal if custom_goal is not None else ""
                    timeout = timeout_seconds if timeout_seconds is not None else None
                    cursor.execute("INSERT INTO chats (chat_id, custom_role, custom_goal, timeout_seconds) VALUES (?, ?, ?, ?)", (chat_id, role, goal, timeout))
                
                conn.commit()
                logger.info(f"Updated settings for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error updating chat settings for {chat_id}: {e}")

    def add_message(self, chat_id: int, role: str, content: str):
        """Add a message to the history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding message for chat {chat_id}: {e}")

    def get_chat_history(self, chat_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieve the last N messages for a chat."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Get last N messages, ordered by timestamp desc, then reverse to get chronological order
                cursor.execute("""
                    SELECT role, content FROM (
                        SELECT role, content, timestamp 
                        FROM messages 
                        WHERE chat_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ) ORDER BY timestamp ASC
                """, (chat_id, limit))
                
                rows = cursor.fetchall()
                return [{"role": row[0], "content": row[1]} for row in rows]
        except Exception as e:
            logger.error(f"Error getting history for chat {chat_id}: {e}")
            return []

    def clear_history(self, chat_id: int):
        """Clear message history for a chat."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
                conn.commit()
                logger.info(f"Cleared history for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error clearing history for chat {chat_id}: {e}")

    def cleanup_old_messages(self, limit: int = MAX_HISTORY_MESSAGES):
        """Delete messages exceeding the limit for each chat, keeping the newest ones."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all chat_ids that have messages
                cursor.execute("SELECT DISTINCT chat_id FROM messages")
                chat_ids = [row[0] for row in cursor.fetchall()]
                
                deleted_count = 0
                for chat_id in chat_ids:
                    # Logic: Delete messages where id NOT IN (SELECT id FROM messages WHERE chat_id=? ORDER BY timestamp DESC LIMIT ?)
                    # But SQLite DELETE with LIMIT/OFFSET is tricky. Easier to find the cut-off timestamp or ID.
                    # Or use a subquery DELETE.
                    
                    cursor.execute("""
                        DELETE FROM messages 
                        WHERE chat_id = ? AND id NOT IN (
                            SELECT id FROM messages 
                            WHERE chat_id = ? 
                            ORDER BY timestamp DESC, id DESC 
                            LIMIT ?
                        )
                    """, (chat_id, chat_id, limit))
                    deleted_count += cursor.rowcount
                
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"Cleanup finished. Deleted {deleted_count} old messages.")
                else:
                    logger.info("Cleanup finished. No old messages to delete.")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")
