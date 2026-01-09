---
id: tasks
updated: 2025-12-26
---

# Tasks (канбан)

## TODO

- [~] EP 001 — Stabilization & Fixes
  - [x] T 001.1 — Kill duplicate bot instances (TelegramConflictError)
  - [~] T 001.2 — Resolve "Unknown model" error
      - [ ] REFLECT — Why DB settings persist old model ID?
      - [ ] CONSULT — Instruction to user to run /model command
  - [~] T 001.3 — Verify Fix (Restart & Test)
      - [x] Fix Code & Database mismatch
      - [x] Valid response from API (Blocked by Rate Limit on Provider)
  - [ ] T 001.4 — Implement Auto-Fallback to Default Model (Resilience)

## TODO (Upcoming)

- [x] EP 002 — Chat Moderation (Neural)
  - [x] T 002.1 — Database: create `grey_list` table & DAO methods
  - [x] T 002.2 — Moderator Logic: implementation of LLM classification & prompt assembly
  - [x] T 002.3 — Handler: integration into message flow & Telegram restrictions (Mute/Ban)
  - [x] T 002.4 — Scheduler: monthly grey list cleanup task
  - [x] T 002.5 — Admin UI: commands for moderation settings

- [/] EP 003 — Multi-Group Moderation Isolation
  - [/] T 003.1 — Planning & Specs: Update .memory files
  - [ ] T 003.2 — Database: Add `chat_context` column & update DAO
  - [ ] T 003.3 — Moderator: Dynamic context passing
  - [ ] T 003.4 — Admin: `/groupabout` command & strict admin checks
  - [ ] T 003.5 — Verification: Test multi-group isolation
