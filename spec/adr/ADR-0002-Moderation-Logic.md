# ADR-0002: Neural Network Chat Moderation

## Status
Proposed

## Context
There is a need to moderate Telegram chats to prevent insults and spam. Traditional keyword-based filters are often too rigid or too loose. We have an existing integration with OpenRouter (LLM).

## Decision
1. **Model**: Use `gpt-4o-mini` (via OpenRouter) for message analysis due to its low cost and high reasoning capability for context.
2. **Contextual Analysis**: Pass the last 5 messages and a static "Chat Context" to the LLM to distinguish between relevant content and spam.
3. **Grey List Algorithm**:
   - Every violation is recorded in a `grey_list` table.
   - **1st violation**: Warning to the user, user ID added to the grey list.
   - **2nd violation**: Restriction of rights (Mute or Ban, depending on bot settings).
4. **Sanitation**: The grey list table is cleared once a month via a scheduled task.
5. **Config**: Prompt and Chat Context are stored in external `.md` files for easier maintenance.

## Consequences
- Increased API costs (per message check).
- Potential latency (approx. 1-2 seconds) for moderation feedback.
- Requires bot admin rights in the chat.
