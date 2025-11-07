import random

# --- Set of random phrases for emoji responses ---
EMOJI_RESPONSES = [
    "😀 Great emoji! Send another one?",
    "😎 Super mood!",
    "😉 You choose well!",
    "😂 I don't even know what to say!",
    "🤖 Emojis accepted, captain!",
    "You're on fire today!",
    "Lol"
]

def get_emoji_response():
    return random.choice(EMOJI_RESPONSES)