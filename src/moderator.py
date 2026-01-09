import os
import json
import logging
import aiofiles
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from config import MODEL_CONFIGS, DEFAULT_MODEL

logger = logging.getLogger(__name__)

class Moderator:
    def __init__(self, model: str = DEFAULT_MODEL):
        model_config = MODEL_CONFIGS.get(model)
        api_key = model_config.get("api_key") if model_config else None
        
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.prompt_path = "prompting/moderation_prompt.md"

    async def _read_file(self, path: str) -> str:
        try:
            async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return ""

    async def check_message(self, text: str, history: List[Dict[str, str]], chat_context: str = "") -> Dict:
        """
        Check message for violations using LLM.
        """
        try:
            prompt_template = await self._read_file(self.prompt_path)
            
            if not prompt_template:
                logger.error("Moderation prompt template is empty or missing.")
                return {"status": "ok", "category": "none", "action_required": False}

            # Format history for LLM
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
            
            # Use default context if none provided
            ctx = chat_context if chat_context else "Общий чат. Ограничений по тематике нет."
            
            # Compose system message
            system_msg = prompt_template.format(
                static_chat_context=ctx,
                message_text=text
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"History:\n{history_str}\n\nCurrent Message: {text}"}
                ],
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            
            # Log raw response for debugging
            logger.info(f"Raw moderation response: {result_text}")
            
            # Try to extract JSON from response
            if result_text:
                result_text = result_text.strip()
                # Try to find JSON object in response
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    result_text = result_text[start_idx:end_idx + 1]
                
                result = json.loads(result_text)
                logger.info(f"Moderation result: {result}")
                return result
            else:
                logger.warning("Empty response from moderation API")
                return {"status": "ok", "category": "none", "action_required": False}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in moderation: {e}. Raw response: {result_text[:200] if result_text else 'None'}")
            return {"status": "ok", "category": "none", "action_required": False}
        except Exception as e:
            logger.error(f"Error checking message for moderation: {e}")
            return {"status": "ok", "category": "none", "action_required": False}
