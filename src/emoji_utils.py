import regex

# --- Check if string contains only emojis ---
def is_only_emoji(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    emoji_pattern = regex.compile(r'^(?:[\p{Emoji}\p{Emoji_Presentation}\p{Emoji_Modifier}\p{Emoji_Modifier_Base}\p{Emoji_Component}]+)$', flags=regex.UNICODE)
    return bool(emoji_pattern.fullmatch(text))