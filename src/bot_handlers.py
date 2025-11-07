import asyncio
from aiogram import types
from src.config import RESPONSE_DELAY, MAX_HISTORY_MESSAGES
from src.responses import get_emoji_response
from src.emoji_utils import is_only_emoji
from src.api_client import get_voidai_response
from src.logging_config import logger
from src.chat_state_manager import active_chats

# Global variable to store the bot instance - will be set from main module
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

def get_bot_instance():
    return _bot_instance

# --- /start command handler ---
async def cmd_start(message: types.Message):
    logger.info(f"Received /start command from user {message.from_user.id} in chat {message.chat.id}")
    await message.answer("👋 Hi! I'm a smart bot. Write me something and I'll reply! What shall we talk about?")


# --- /startconv command ---
async def start_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /startconv command from user {message.from_user.id} in chat {chat_id}")

    if chat_id in active_chats:
        await message.answer("🤖 Conversation mode is already activated in this chat.")
        logger.info(f"Conversation mode is already active in chat {chat_id}")
        return

    active_chats[chat_id] = {
        "message_history": [],
        "timer": None,
        "is_waiting_for_user": False,
        "reply_to_message_id": None  # Add field to store message ID to reply to
    }
    logger.debug(f"Chat state {chat_id} initialized: {active_chats[chat_id]}")
    await message.answer("🤖 Conversation mode activated. I will join the conversation if there is a pause.")
    logger.info(f"Conversation mode activated in chat {chat_id}")


# --- /stopconv command ---
async def stop_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /stopconv command from user {message.from_user.id} in chat {chat_id}")

    if chat_id not in active_chats:
        await message.answer("🤖 Conversation mode is not activated in this chat.")
        logger.info(f"Conversation mode is not active in chat {chat_id}")
        return

    state = active_chats[chat_id]
    if state["timer"]:
        state["timer"].cancel()
        logger.info(f"Timer cancelled for chat {chat_id}")

    del active_chats[chat_id]
    logger.debug(f"Chat state {chat_id} deleted.")
    await message.answer("🤖 Conversation mode deactivated.")
    logger.info(f"Conversation mode deactivated in chat {chat_id}")


# --- Function to generate and send response ---
async def generate_response(chat_id: int):
    logger.info(f"Response generation started for chat {chat_id}")
    state = active_chats.get(chat_id)
    logger.debug(f"Chat state {chat_id} before response generation: {state}")

    if not state:
        logger.warning(f"Chat {chat_id} is not active during response generation. Stopping execution.")
        return

    if state["is_waiting_for_user"]:
        logger.info(f"Bot is waiting for user response in chat {chat_id}. Stopping execution.")
        return

    try:
        bot = get_bot_instance()
        if not bot:
            logger.error(f"Bot instance not available in generate_response for chat {chat_id}")
            return
            
        await bot.send_chat_action(chat_id, "typing")
        logger.debug(f"Sent 'typing' indicator to chat {chat_id}")

        logger.debug(f"Message history for VoidAI API in chat {chat_id}: {state['message_history']}")
        generated_text = await get_voidai_response(state["message_history"])
        logger.info(f"Received response from Gemini for chat {chat_id}: {generated_text}")

        await bot.send_message(chat_id, generated_text, reply_to_message_id=state.get("reply_to_message_id"))
        logger.info(f"Response sent to chat {chat_id}, replying to message ID: {state.get('reply_to_message_id')}")

        state["message_history"].append({"role": "assistant", "content": generated_text})  # Add bot's response to history
        # Limit message history to the last MAX_HISTORY_MESSAGES messages
        if len(state["message_history"]) > MAX_HISTORY_MESSAGES:
            state["message_history"] = state["message_history"][-MAX_HISTORY_MESSAGES:]
        state["is_waiting_for_user"] = True
        logger.info(f"is_waiting_for_user flag set and bot's response added to history for chat {chat_id}")
        # Добавляем лог для проверки состояния message_history после успешной отправки ответа
        logger.debug(f"Message history for chat {chat_id} after bot's response: {state['message_history']}")

    except Exception as e:
        logger.error(f"Error generating or sending response in chat {chat_id}: {e}")
        if bot:
            await bot.send_message(chat_id, "🤖 Sorry, an error occurred while generating the response.")
        # Reset chat state after error to avoid reprocessing old messages
        if state:
            state["message_history"] = []
            state["is_waiting_for_user"] = True
            logger.info(f"Chat state {chat_id} reset after error. History cleared, is_waiting_for_user set to True.")


# --- Handler for any messages ---
async def handle_message(message: types.Message):
    bot = get_bot_instance()
    if not bot:
        logger.error(f"Bot instance not available in handle_message for chat {message.chat.id}")
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_text = message.text

    logger.info(f"Received message from {user_id} in chat {chat_id}: {user_text}")

    if chat_id not in active_chats:
        logger.info(f"Chat {chat_id} is not active, ignoring message from {user_id}: {user_text}")
        return

    state = active_chats[chat_id]
    logger.debug(f"Current chat state {chat_id}: {state}")

    # Store the message ID to reply to only if the user is replying to the bot
    state["reply_to_message_id"] = None
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        state["reply_to_message_id"] = message.message_id
        logger.debug(f"Set reply_to_message_id for chat {chat_id} to {message.message_id} (reply to bot)")
    else:
        logger.debug(f"reply_to_message_id for chat {chat_id} set to None (not a reply to bot)")

    if state["is_waiting_for_user"]:
        state["is_waiting_for_user"] = False
        logger.info(f"is_waiting_for_user flag reset for chat {chat_id}")

    if user_text:
        # Добавляем лог для проверки содержимого message.reply_to_message
        logger.debug(f"Message reply_to_message for chat {chat_id}: {message.reply_to_message}")
        if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
            quoted_text = message.reply_to_message.text
            # Check if this message is already in history to avoid duplicates
            if not any(msg.get("role") == "assistant" and msg.get("content") == quoted_text for msg in state["message_history"]):
                state["message_history"].append({"role": "assistant", "content": quoted_text})
                logger.debug(f"Quoted bot message added to history for chat {chat_id}: {quoted_text}")
        
        if is_only_emoji(user_text):
            response_text = get_emoji_response()
            await message.answer(response_text)
            logger.info(f"Sent emoji response to chat {chat_id}: {response_text}")
            # Update is_waiting_for_user flag after emoji response
            state["is_waiting_for_user"] = True
            logger.info(f"is_waiting_for_user flag set after emoji response for chat {chat_id}")
            return  # Stop further processing if it's only emojis
        
        state["message_history"].append({"role": "user", "content": user_text})
        # Limit message history to the last MAX_HISTORY_MESSAGES messages
        if len(state["message_history"]) > MAX_HISTORY_MESSAGES:
            state["message_history"] = state["message_history"][-MAX_HISTORY_MESSAGES:]
        logger.debug(f"Message added to chat history {chat_id}. History: {state['message_history']}")

    if state["timer"]:
        state["timer"].cancel()
        logger.debug(f"Previous timer cancelled for chat {chat_id}")

    # Create a proper async task for the timer to handle cancellation correctly
    async def delayed_response(chat_id):
        await asyncio.sleep(RESPONSE_DELAY)
        await generate_response(chat_id)

    state["timer"] = asyncio.create_task(delayed_response(chat_id))
    logger.info(f"New timer task created for {RESPONSE_DELAY} seconds for chat {chat_id}")