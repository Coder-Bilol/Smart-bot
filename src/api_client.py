from openai import OpenAI, APIError
from config import MODEL_CONFIGS, DEFAULT_MODEL
from logging_config import logger

# We no longer instantiate a global client because keys differ per model.

# --- Function to get response from LLM (OpenRouter) ---
async def get_llm_response(message_history: list, model: str = DEFAULT_MODEL) -> str:
    logger.debug(f"Sending request to OpenRouter. Model: {model}")
    
    # Retrieve configuration for the specific model
    model_config = MODEL_CONFIGS.get(model)
    if not model_config:
        logger.error(f"Configuration for model {model} not found.")
        raise ValueError(f"Unknown model: {model}")
        
    api_key = model_config.get("api_key")
    if not api_key:
        logger.error(f"API key for model {model} is not set in environment variables.")
        raise ValueError(f"API key missing for model: {model}")

    try:
        # Initialize client with the specific key
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/Coder-Bilol/Smart-bot", 
                "X-Title": "Smart Bot", 
            },
            model=model,
            messages=message_history
        )
        response_content = completion.choices[0].message.content
        logger.debug("Received response from OpenRouter.")
        return response_content

    except APIError as e:
        logger.error(f"OpenAI API Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unknown error when getting response from OpenRouter: {e}")
        raise

# --- Function to check API availability ---
async def check_api_availability():
    logger.info("Checking OpenRouter API availability (checking default model key)...")
    
    # Check the default model's key as a proxy for availability
    model = DEFAULT_MODEL
    model_config = MODEL_CONFIGS.get(model)
    
    if not model_config or not model_config.get("api_key"):
        logger.error(f"Default model {model} configuration or API key is missing.")
        return False
        
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=model_config.get("api_key"),
        )
        # Simple test request to verify key and connection
        client.models.list()
        logger.info(f"OpenRouter API verification successful using key for {model}.")
        return True
    except APIError as e:
        logger.error(f"OpenRouter API check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unknown error when checking OpenRouter API: {e}")
        return False