import httpx
import asyncio
from config import VOIDAI_API_KEY, VOIDAI_MODEL
from logging_config import logger

# --- Function to get response from VoidAI ---
async def get_voidai_response(message_history: list) -> str:
    url = "https://api.voidai.app/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {VOIDAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": VOIDAI_MODEL,
        "messages": message_history
    }
    # Security fix: Do not log headers containing API key
    logger.debug(f"Sending request to VoidAI API. URL: {url}, Payload: {payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30)  # Increase timeout
            logger.debug(f"Received response from VoidAI API. Status: {response.status_code}, Body: {response.text}")
            response.raise_for_status()  # Raise an exception for 4xx/5xx status codes
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error when requesting VoidAI API: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error when requesting VoidAI API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unknown error when getting response from VoidAI API: {e}")
            raise


# --- Function to check VoidAI API availability ---
async def check_voidai_api():
    logger.info("Checking VoidAI API availability...")
    url = "https://api.voidai.app/v1/models"  # Endpoint to get list of models
    headers = {
        "Authorization": f"Bearer {VOIDAI_API_KEY}"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info("VoidAI API is available. API key is valid.")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when checking VoidAI API: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Network error when checking VoidAI API: {e}")
        return False
    except Exception as e:
        logger.error(f"Unknown error when checking VoidAI API: {e}")
        return False