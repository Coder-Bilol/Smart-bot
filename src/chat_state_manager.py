from database import DatabaseManager

# Initialize Database Manager
db = DatabaseManager()

# Dictionary to store transient chat states (timers, flags)
# Structure:
# {
#   chat_id: {
#       "timer": asyncio.Task | None,
#       "is_waiting_for_user": bool,
#       "reply_to_message_id": int | None
#   }
# }
active_chats = {}