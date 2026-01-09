# This project lives on GitHub
import asyncio
from aiogram import Bot, Dispatcher
from config import API_TOKEN
from api_client import check_api_availability
from logging_config import logger

# Import handlers from new module structure
from handlers.admin import router as admin_router
from handlers.chat import router as chat_router

from chat_state_manager import active_chats, db
# Ensure transient state helper is imported if needed or just define logic inline
# Actually, chat.py handles ensure_transient_state when commands runs.
# Here we just need to populate active_chats dict.

# --- Bot and Dispatcher Initialization ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Background Tasks ---
async def scheduler():
    """Background task to perform periodic maintenance."""
    while True:
        try:
            from datetime import datetime
            now = datetime.now()
            # If it's the first day of the month and early morning (e.g., 03:00)
            if now.day == 1 and now.hour == 3:
                logger.info("First day of the month detected. Resetting grey list...")
                await db.reset_grey_list()
                # Wait for an hour to avoid multiple resets in the same hour
                await asyncio.sleep(3600)
            
            # Check every hour
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            await asyncio.sleep(60)

# --- Register routers ---
dp.include_router(admin_router)
dp.include_router(chat_router)


# --- Main function ---
async def main():
    print("Bot launched! Press Ctrl+C to stop.")
    
    # Initialize Database (Async)
    await db.init_db()
    
    # Restore active chats state
    active_chat_ids = await db.get_active_chats()
    count_restored = 0
    for chat_id in active_chat_ids:
        if chat_id not in active_chats:
            active_chats[chat_id] = {
                "timer": None,
                "is_waiting_for_user": False,
                "reply_to_message_id": None
            }
            count_restored += 1
    
    logger.info(f"Restored {count_restored} active chats from database.")

    if not await check_api_availability():
        logger.error("LLM API is unavailable or API key is invalid. Bot will not be launched.")
        return
        
    # Start scheduler
    asyncio.create_task(scheduler())
    
    await dp.start_polling(bot, close_bot_session=True)

# Main function
if __name__ == "__main__":
    asyncio.run(main())