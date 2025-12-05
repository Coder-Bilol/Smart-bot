import asyncio
import os
from aiogram import types, Bot
from aiogram.filters import CommandObject
from config import RESPONSE_DELAY, MAX_HISTORY_MESSAGES
from responses import get_emoji_response
from emoji_utils import is_only_emoji
from api_client import get_voidai_response
from logging_config import logger
from chat_state_manager import active_chats, db

# --- Helper to read prompt files ---
def read_prompt_file(filename):
    try:
        with open(os.path.join("prompting", filename), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading prompt file {filename}: {e}")
        return ""

# --- Helper to check admin status ---
async def is_admin(message: types.Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return chat_member.status in ["administrator", "creator"]

# --- Helper to ensure transient state exists ---
def ensure_transient_state(chat_id):
    if chat_id not in active_chats:
        active_chats[chat_id] = {
            "timer": None,
            "is_waiting_for_user": False,
            "reply_to_message_id": None
        }

# --- /start command handler ---
async def cmd_start(message: types.Message):
    logger.info(f"Received /start command from user {message.from_user.id} in chat {message.chat.id}")
    await message.answer("👋 Hi! I'm a smart bot. Write me something and I'll reply! What shall we talk about?")


# --- /role command handler ---
async def cmd_role(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the role.")
        return

    chat_id = message.chat.id
    custom_role = command.args
    
    # Ensure DB record exists (implicitly handled by update, but good to know)
    
    if not custom_role:
        # Reset role
        db.update_chat_settings(chat_id, custom_role="")
        await message.answer("🔄 Custom role reset.")
        logger.info(f"Custom role reset for chat {chat_id}")
    else:
        db.update_chat_settings(chat_id, custom_role=custom_role)
        await message.answer(f"🎭 Custom role set to: {custom_role}")
        logger.info(f"Custom role set for chat {chat_id}: {custom_role}")


# --- /goal command handler ---
async def cmd_goal(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the goal.")
        return

    chat_id = message.chat.id
    custom_goal = command.args

    if not custom_goal:
        # Reset goal
        db.update_chat_settings(chat_id, custom_goal="")
        await message.answer("🔄 Custom goal reset.")
        logger.info(f"Custom goal reset for chat {chat_id}")

# --- /timeout command handler ---
async def cmd_timeout(message: types.Message, command: CommandObject):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can change the timeout.")
        return

    chat_id = message.chat.id
    
    if not command.args:
        # Reset timeout
        db.update_chat_settings(chat_id, timeout_seconds=None)
        await message.answer("🔄 Timeout reset to default.")
        logger.info(f"Timeout reset for chat {chat_id}")
    else:
        try:
            timeout = int(command.args)
            if timeout < 0:
                raise ValueError
            
            db.update_chat_settings(chat_id, timeout_seconds=timeout)
            await message.answer(f"⏱ Timeout set to: {timeout} seconds")
            logger.info(f"Timeout set for chat {chat_id}: {timeout}")
            
            # Reset active state to force reload of settings on next message
            if chat_id in active_chats:
                # We don't delete the state completely, just ensure settings are refreshed? 
                # Actually, our generate_response pulls fresh settings every time. 
                # But the timer length is decided in handle_message. 
                # So next message will use new timeout.
                pass
                
        except ValueError:
            await message.answer("⚠ Please provide a valid positive integer for seconds.")


# --- /statusconv command handler ---
async def cmd_statusconv(message: types.Message):
    if not await is_admin(message):
        await message.answer("🚫 Only admins can view the status.")
        return

    chat_id = message.chat.id
    
    # Get base prompts
    base_role = read_prompt_file("role_prompt.md")
    base_goal = read_prompt_file("goal_prompt.md")
    
    # Get custom prompts from DB
    settings = db.get_chat_settings(chat_id)
    custom_role = settings.get("custom_role", "")
    custom_goal = settings.get("custom_goal", "")
    pk_timeout = settings.get("timeout_seconds")
    
    timeout_display = f"{pk_timeout}s" if pk_timeout is not None else f"{RESPONSE_DELAY}s (default)"
    
    # Construct status message
    status_msg = (
        f"📋 **Current Conversation Status**\n\n"
        f"**# Role**\n"
        f"{base_role}\n"
        f"{custom_role}\n\n"
        f"**# Goal**\n"
        f"{base_goal}\n"
        f"{custom_goal}\n\n"
        f"**# Timeout**\n"
        f"{timeout_display}"
    )
    
    await message.answer(status_msg, parse_mode="Markdown")
    logger.info(f"Sent statusconv response to chat {chat_id}")


# --- /startconv command ---
async def start_conversation(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Received /startconv command from user {message.from_user.id} in chat {chat_id}")

    if chat_id in active_chats:
        await message.answer("🤖 Conversation mode is already activated in this chat.")
        logger.info(f"Conversation mode is already active in chat {chat_id}")
        return

    ensure_transient_state(chat_id)
    
    # Ensure DB entry exists for this chat
    db.update_chat_settings(chat_id) # Creates default if not exists
    
    logger.debug(f"Chat state {chat_id} initialized.")
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
    
    # Optional: Clear history from DB on stop? 
    # For now, let's keep it persistent as requested ("save for each chat").
    # If user wants to clear, maybe we need a /clear command.
    
    logger.debug(f"Chat state {chat_id} deleted (transient only).")
    await message.answer("🤖 Conversation mode deactivated.")
    logger.info(f"Conversation mode deactivated in chat {chat_id}")


# --- Function to generate and send response ---
async def generate_response(chat_id: int, bot: Bot):
    logger.info(f"Response generation started for chat {chat_id}")
    state = active_chats.get(chat_id)
    
    if not state:
        logger.warning(f"Chat {chat_id} is not active during response generation. Stopping execution.")
        return

    if state["is_waiting_for_user"]:
        logger.info(f"Bot is waiting for user response in chat {chat_id}. Stopping execution.")
        return

    try:
        await bot.send_chat_action(chat_id, "typing")
        logger.debug(f"Sent 'typing' indicator to chat {chat_id}")

        # --- Construct Structured Prompt ---
        base_role = read_prompt_file("role_prompt.md")
        base_goal = read_prompt_file("goal_prompt.md")
        
        settings = db.get_chat_settings(chat_id)
        custom_role = settings.get("custom_role", "")
        custom_goal = settings.get("custom_goal", "")

        system_prompt = f"# Role\n{base_role}\n{custom_role}\n\n# Goal\n{base_goal}\n{custom_goal}"
        
        # Get history from DB
        history = db.get_chat_history(chat_id, limit=MAX_HISTORY_MESSAGES)
        
        # Create a copy of history and prepend system prompt
        full_history = [{"role": "system", "content": system_prompt}] + history

        logger.debug(f"Sending structured prompt to VoidAI for chat {chat_id}. System Prompt length: {len(system_prompt)}")
        generated_text = await get_voidai_response(full_history)
        logger.info(f"Received response from Gemini for chat {chat_id}: {generated_text}")

        await bot.send_message(chat_id, generated_text, reply_to_message_id=state.get("reply_to_message_id"))
        logger.info(f"Response sent to chat {chat_id}, replying to message ID: {state.get('reply_to_message_id')}")

        # Save bot response to DB
        db.add_message(chat_id, "assistant", generated_text)
        
        state["is_waiting_for_user"] = True
        logger.info(f"is_waiting_for_user flag set and bot's response added to history for chat {chat_id}")

    except Exception as e:
        logger.error(f"Error generating or sending response in chat {chat_id}: {e}")
        if bot:
            await bot.send_message(chat_id, "🤖 Sorry, an error occurred while generating the response.")
        # Reset transient state after error
        if state:
            state["is_waiting_for_user"] = True
            logger.info(f"Chat state {chat_id} reset after error.")


# --- Handler for any messages ---
async def handle_message(message: types.Message):
    bot = message.bot
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_text = message.text

    logger.info(f"Received message from {user_id} in chat {chat_id}: {user_text}")

    if chat_id not in active_chats:
        logger.info(f"Chat {chat_id} is not active, ignoring message from {user_id}: {user_text}")
        return

    state = active_chats[chat_id]
    
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
        # Check if replying to bot's message to add context
        if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
            quoted_text = message.reply_to_message.text
            # We don't strictly need to add quoted text to DB history if it's already there,
            # but the logic before was checking if it's in history.
            # With DB, we assume the bot's message is already in DB.
            # So we just proceed to add user message.
            pass
        
        if is_only_emoji(user_text):
            response_text = get_emoji_response()
            await message.answer(response_text)
            logger.info(f"Sent emoji response to chat {chat_id}: {response_text}")
            state["is_waiting_for_user"] = True
            return  # Stop further processing if it's only emojis
        
        # Save user message to DB
        db.add_message(chat_id, "user", user_text)
        logger.debug(f"Message added to chat history {chat_id}.")

    if state["timer"]:
        state["timer"].cancel()
        logger.debug(f"Previous timer cancelled for chat {chat_id}")

    # Determine Delay
    # Check if immediate reply is needed (user cited bot)
    is_quote_reply = False
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        is_quote_reply = True
    
    if is_quote_reply:
         delay = 0
         logger.info(f"Immediate reply trigger for chat {chat_id} (quote)")
    else:
        # Fetch timeout from DB or config
        settings = db.get_chat_settings(chat_id)
        custom_timeout = settings.get("timeout_seconds")
        
        # If custom_timeout is None (from DB), it might be returned as None.
        # Check if it's a valid number
        if custom_timeout is not None and isinstance(custom_timeout, int):
             delay = custom_timeout
        else:
             delay = RESPONSE_DELAY
        
        logger.info(f"Scheduling response in {delay} seconds for chat {chat_id}")

    # Create a proper async task for the timer
    async def delayed_response(chat_id, bot_instance, wait_time):
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        await generate_response(chat_id, bot_instance)

    state["timer"] = asyncio.create_task(delayed_response(chat_id, bot, delay))
    logger.info(f"New timer task created for {delay} seconds for chat {chat_id}")