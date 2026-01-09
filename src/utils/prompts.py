import os
import logging

logger = logging.getLogger(__name__)

def read_prompt_file(filename):
    try:
        # Assuming run context is root, prompts are in ./prompting/
        path = os.path.join("prompting", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading prompt file {filename}: {e}")
        return ""
