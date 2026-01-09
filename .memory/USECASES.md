# Use Cases

## UC-1: Activation
**Actor**: Admin
**Description**: Включение режима разговора в чате.
**Flow**:
1. User sends `/startconv`.
2. Bot checks DB.
3. Bot saves `is_active=1`.
4. Bot sends confirmation.
**Acceptance Criteria**: Бот начинает реагировать на сообщения.

## UC-2: Auto-Reply (Conversation)
**Actor**: User (Any)
**Description**: Бот вклинивается в разговор.
**Pre-conditions**: Режим активен, `is_waiting_for_user=False`.
**Flow**:
1. User sends message.
2. Bot saves message to DB.
3. Bot resets/starts timer (Debounce `RESPONSE_DELAY`).
4. Timer expires -> Bot generates answer -> Sends reply.
5. Bot sets `is_waiting_for_user=True`.

## UC-3: Reply to Bot
**Actor**: User
**Description**: Ответ на реплику бота вызывает мгновенную реакцию.
**Flow**:
1. User replies to Bot's message.
2. Bot detects reply.
3. Bot cancels delay (Delay = 0).
4. Bot generates answer immediately.

## UC-4: Change Model
**Actor**: Admin
**Description**: Смена LLM "на лету".
**Flow**:
1. Admin sends `/model`.
2. Bot shows inline keyboard.
3. Admin clicks button.
4. Bot updates `model` in DB.
5. Bot uses new model for next request.

## UC-5: Chat Moderation
**Actor**: User (Any) / AI Moderator
**Description**: Автоматическое пресечение нарушений правил. Просмотр списка нарушителей доступен всем.
**Flow**:
1. User sends message.
2. Bot checks message via LLM (with context).
3. LLM returns "violation".
4. Bot checks `grey_list`.
5. If clean -> Warning + add to `grey_list`.
6. If already in `grey_list` -> Apply restriction (Mute/Ban).
7. Any user sends `/graylist` -> Bot shows violators for current chat.
8. Monthly -> Clear `grey_list`.
## UC-6: Personal Chat Context
**Actor**: Group Admin
**Description**: Настройка специфики модерации для конкретной группы.
**Flow**:
1. Admin sends `/groupabout [description]`.
2. Bot verifies that sender is an actual group admin.
3. Bot updates `chat_context` in `chats` table for current `chat_id`.
4. Bot uses this context in all future moderation checks for this group.
**Acceptance Criteria**: ИИ модератор в Группе А наказывает за спам кроссовками, а в Группе Б (барахолка) — нет, если так настроил админ.
