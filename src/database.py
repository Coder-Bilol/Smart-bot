import aiosqlite
import logging
from typing import List, Dict, Optional
from config import MAX_HISTORY_MESSAGES, DEFAULT_MODEL

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path

    async def init_db(self):
        """Initialize the database tables."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create chats table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER PRIMARY KEY,
                        custom_role TEXT,
                        custom_goal TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Try to add columns if they don't exist (Migration)
                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN timeout_seconds INTEGER DEFAULT NULL")
                except aiosqlite.OperationalError:
                    pass

                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN model TEXT DEFAULT NULL")
                except aiosqlite.OperationalError:
                    pass

                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN is_active INTEGER DEFAULT 0")
                except aiosqlite.OperationalError:
                    pass

                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN mod_action TEXT DEFAULT 'mute'")
                except aiosqlite.OperationalError:
                    pass

                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN strict_threshold INTEGER DEFAULT 2")
                except aiosqlite.OperationalError:
                    pass

                try:
                    await db.execute("ALTER TABLE chats ADD COLUMN chat_context TEXT DEFAULT NULL")
                except aiosqlite.OperationalError:
                    pass
                
                # Create messages table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                """)

                # Create grey_list table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS grey_list (
                        user_id INTEGER,
                        chat_id INTEGER,
                        violation_count INTEGER DEFAULT 0,
                        last_violation_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, chat_id)
                    )
                """)
                
                await db.commit()
                logger.info("Database initialized successfully.")
                
            # Perform cleanup on startup
            await self.cleanup_old_messages()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    async def get_chat_settings(self, chat_id: int) -> Dict[str, any]:
        """Retrieve settings for a chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT custom_role, custom_goal, timeout_seconds, model, is_active, mod_action, strict_threshold, chat_context FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        model = row[3] if row[3] else DEFAULT_MODEL
                        is_active = bool(row[4])
                        return {
                            "custom_role": row[0],
                            "custom_goal": row[1],
                            "timeout_seconds": row[2],
                            "model": model,
                            "is_active": is_active,
                            "mod_action": row[5] if len(row) > 5 else "mute",
                            "strict_threshold": row[6] if len(row) > 6 else 2,
                            "chat_context": row[7] if len(row) > 7 else ""
                        }
                    return {
                        "custom_role": "",
                        "custom_goal": "",
                        "timeout_seconds": None,
                        "model": DEFAULT_MODEL,
                        "is_active": False,
                        "mod_action": "mute",
                        "strict_threshold": 2,
                        "chat_context": ""
                    }
        except Exception as e:
            logger.error(f"Error getting chat settings for {chat_id}: {e}")
            return {"custom_role": "", "custom_goal": "", "timeout_seconds": None, "model": DEFAULT_MODEL, "is_active": False, "mod_action": "mute", "strict_threshold": 2, "chat_context": ""}

    async def update_chat_settings(self, chat_id: int, custom_role: Optional[str] = None, custom_goal: Optional[str] = None, timeout_seconds: Optional[int] = None, model: Optional[str] = None, is_active: Optional[bool] = None, mod_action: Optional[str] = None, strict_threshold: Optional[int] = None, chat_context: Optional[str] = None):
        """Update or insert chat settings."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if chat exists
                async with db.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    if custom_role is not None:
                        await db.execute("UPDATE chats SET custom_role = ? WHERE chat_id = ?", (custom_role, chat_id))
                    if custom_goal is not None:
                        await db.execute("UPDATE chats SET custom_goal = ? WHERE chat_id = ?", (custom_goal, chat_id))
                    if timeout_seconds is not None:
                        await db.execute("UPDATE chats SET timeout_seconds = ? WHERE chat_id = ?", (timeout_seconds, chat_id))
                    if model is not None:
                        await db.execute("UPDATE chats SET model = ? WHERE chat_id = ?", (model, chat_id))
                    if is_active is not None:
                         val = 1 if is_active else 0
                         await db.execute("UPDATE chats SET is_active = ? WHERE chat_id = ?", (val, chat_id))
                    if mod_action is not None:
                        await db.execute("UPDATE chats SET mod_action = ? WHERE chat_id = ?", (mod_action, chat_id))
                    if strict_threshold is not None:
                        await db.execute("UPDATE chats SET strict_threshold = ? WHERE chat_id = ?", (strict_threshold, chat_id))
                    if chat_context is not None:
                        await db.execute("UPDATE chats SET chat_context = ? WHERE chat_id = ?", (chat_context, chat_id))

                else:
                    role = custom_role if custom_role is not None else ""
                    goal = custom_goal if custom_goal is not None else ""
                    timeout = timeout_seconds if timeout_seconds is not None else None
                    mdl = model if model is not None else DEFAULT_MODEL
                    act = 1 if is_active else 0
                    mod_act = mod_action if mod_action is not None else "mute"
                    thr = strict_threshold if strict_threshold is not None else 2
                    ctx = chat_context if chat_context is not None else ""
                    
                    await db.execute(
                        "INSERT INTO chats (chat_id, custom_role, custom_goal, timeout_seconds, model, is_active, mod_action, strict_threshold, chat_context) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (chat_id, role, goal, timeout, mdl, act, mod_act, thr, ctx)
                    )
                
                await db.commit()
                logger.info(f"Updated settings for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error updating chat settings for {chat_id}: {e}")

    async def get_active_chats(self) -> List[int]:
        """Retrieve all active chat IDs."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT chat_id FROM chats WHERE is_active = 1") as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting active chats: {e}")
            return []

    async def add_message(self, chat_id: int, role: str, content: str):
        """Add a message to the history."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
                await db.commit()
        except Exception as e:
            logger.error(f"Error adding message for chat {chat_id}: {e}")

    async def get_chat_history(self, chat_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieve the last N messages for a chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get last N messages
                async with db.execute("""
                    SELECT role, content FROM (
                        SELECT role, content, timestamp 
                        FROM messages 
                        WHERE chat_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ) ORDER BY timestamp ASC
                """, (chat_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    return [{"role": row[0], "content": row[1]} for row in rows]
        except Exception as e:
            logger.error(f"Error getting history for chat {chat_id}: {e}")
            return []

    async def clear_history(self, chat_id: int):
        """Clear message history for a chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
                await db.commit()
                logger.info(f"Cleared history for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error clearing history for chat {chat_id}: {e}")

    async def cleanup_old_messages(self, limit: int = MAX_HISTORY_MESSAGES):
        """Delete messages exceeding the limit for each chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all chat_ids that have messages
                async with db.execute("SELECT DISTINCT chat_id FROM messages") as cursor:
                    rows = await cursor.fetchall()
                    chat_ids = [row[0] for row in rows]
                
                deleted_count = 0
                for chat_id in chat_ids:
                    # SQLite delete logic with subquery
                    await db.execute("""
                        DELETE FROM messages 
                        WHERE chat_id = ? AND id NOT IN (
                            SELECT id FROM messages 
                            WHERE chat_id = ? 
                            ORDER BY timestamp DESC, id DESC 
                            LIMIT ?
                        )
                    """, (chat_id, chat_id, limit))
                    # Note: aiosqlite cursor.rowcount might not be immediately available after execute on connection shorthand
                    # But that's okay for logging purposes
                
                await db.commit()
                logger.info(f"Cleanup finished.")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")

    async def get_violation_count(self, user_id: int, chat_id: int) -> int:
        """Get the number of violations for a user in a specific chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT violation_count FROM grey_list WHERE user_id = ? AND chat_id = ?", 
                    (user_id, chat_id)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting violation count for user {user_id} in chat {chat_id}: {e}")
            return 0

    async def add_violation(self, user_id: int, chat_id: int):
        """Increment violation count for a user in a chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM grey_list WHERE user_id = ? AND chat_id = ?", 
                    (user_id, chat_id)
                ) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    await db.execute(
                        "UPDATE grey_list SET violation_count = violation_count + 1, last_violation_at = CURRENT_TIMESTAMP WHERE user_id = ? AND chat_id = ?",
                        (user_id, chat_id)
                    )
                else:
                    await db.execute(
                        "INSERT INTO grey_list (user_id, chat_id, violation_count) VALUES (?, ?, 1)",
                        (user_id, chat_id)
                    )
                await db.commit()
                logger.info(f"Added violation for user {user_id} in chat {chat_id}")
        except Exception as e:
            logger.error(f"Error adding violation for user {user_id} in chat {chat_id}: {e}")

    async def reset_grey_list(self):
        """Clear the entire grey list (monthly cleanup)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM grey_list")
                await db.commit()
                logger.info("Grey list has been reset.")
        except Exception as e:
            logger.error(f"Error resetting grey list: {e}")

    async def get_grey_list(self, chat_id: int) -> list:
        """Get all users in the grey list for a specific chat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT user_id, violation_count, last_violation_at FROM grey_list WHERE chat_id = ? ORDER BY violation_count DESC",
                    (chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [{"user_id": row[0], "violation_count": row[1], "last_violation_at": row[2]} for row in rows]
        except Exception as e:
            logger.error(f"Error getting grey list for chat {chat_id}: {e}")
            return []
