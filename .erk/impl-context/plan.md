# Plan: Add Suggested Reply Buttons (Objective #8036, Node 1.8)

## Context

The erk-slack-bot currently handles `@erk chat <message>` by streaming an AI agent response and posting the final text. After the response, there's no affordance guiding the user toward next actions. Node 1.8 adds Block Kit buttons with suggested follow-up actions (e.g., "Show Plans", "Tell me more") after each agent chat response. This makes the bot more discoverable and conversational.

**Depends on:** Nodes 1.1–1.6 (done). Node 1.7 (prompts.py, in progress #8124) is independent — buttons don't require the system prompt.

## Design Decisions

1. **Static suggestions** — Use a fixed set of context-aware buttons rather than LLM-generated ones. Avoids extra API cost and complexity. The three buttons cover primary follow-up intents.
2. **Separate message** — Post buttons as a distinct message after all response chunks, avoiding Block Kit complexity in the chunking logic.
3. **Reuse `parse_erk_command`** — Button clicks carry raw command text (e.g., `"plan list"`) as the `value` field. The existing parser handles dispatch, avoiding new routing logic.
4. **Replace buttons on click** — Update the button message to show which option was selected, preventing re-clicks.

## Implementation Steps

### Step 1: Create `suggested_replies.py` (NEW)

**File:** `packages/erkbot/src/erkbot/suggested_replies.py`

- `SuggestedReply` frozen dataclass with `label`, `action_id`, `value` fields
- `CHAT_SUGGESTED_REPLIES` constant tuple with three buttons:
  - "Show Plans" → `value="plan list"` (dispatches `PlanListCommand`)
  - "Tell me more" → `value="chat tell me more about that"` (dispatches `ChatCommand`)
  - "Start fresh" → `value="chat hello, what can you help me with?"` (dispatches `ChatCommand`)
- `build_suggested_replies_blocks(*, replies)` → returns Block Kit `actions` block list
- `build_selected_reply_blocks(*, selected_label, user_id)` → returns replacement block after click

### Step 2: Add config toggle

**File:** `packages/erkbot/src/erkbot/config.py`

Add `enable_suggested_replies: bool = True` to `Settings`. Follows existing default-value pattern for pydantic_settings fields.

### Step 3: Post buttons in `agent_handler.py`

**File:** `packages/erkbot/src/erkbot/agent_handler.py`

Add two keyword-only params to `run_agent_background()`:
- `enable_suggested_replies: bool`
- `suggested_reply_blocks: list[dict[str, object]]`

After posting final response chunks (and after the empty-response fallback), before `success = True`:

```python
if enable_suggested_replies and suggested_reply_blocks:
    try:
        await client.chat_postMessage(
            channel=channel,
            blocks=suggested_reply_blocks,
            text="Suggested follow-ups",
            thread_ts=reply_thread_ts,
        )
    except SlackApiError:
        pass  # Best-effort
```

Buttons are NOT posted on error paths or empty responses.

### Step 4: Wire into `slack_handlers.py`

**File:** `packages/erkbot/src/erkbot/slack_handlers.py`

**4a.** In `ChatCommand` dispatch, pass `enable_suggested_replies` and pre-built `suggested_reply_blocks` to `run_agent_background()`.

**4b.** Add `@app.action(re.compile(r"suggested_reply_.+"))` handler:
1. `await ack()` immediately
2. Update button message → show `"<@user> selected: *label*"` via `chat_update` with `build_selected_reply_blocks()`
3. Extract `value` from action, parse with `parse_erk_command(value)`
4. Dispatch the resulting command (PlanListCommand → run plan list; ChatCommand → run agent background)

**Important:** Action payload structure differs from events:
- Channel: `body["channel"]["id"]`
- User: `body["user"]["id"]`
- Thread: `body["message"]["thread_ts"]`

### Step 5: Tests

**New file:** `packages/erkbot/tests/test_suggested_replies.py`
- `SuggestedReply` is frozen
- `build_suggested_replies_blocks` returns correct Block Kit structure
- `build_selected_reply_blocks` includes user mention
- All `CHAT_SUGGESTED_REPLIES` have `suggested_reply_` prefix

**Modify:** `packages/erkbot/tests/test_agent_handler.py`
- Add `enable_suggested_replies=False, suggested_reply_blocks=[]` to all 4 existing tests
- New: `test_suggested_replies_posted_after_response` (enabled=True → blocks posted)
- New: `test_suggested_replies_not_posted_when_disabled` (enabled=False → no blocks)
- New: `test_suggested_replies_not_posted_on_error` (error path → no blocks)

**Modify:** `packages/erkbot/tests/test_slack_handlers.py`
- Update `FakeApp` to support `action()` method registration
- Test that action handler is registered
- Test ChatCommand passes suggested reply params

**Modify:** `packages/erkbot/tests/test_config.py`
- Test `enable_suggested_replies` defaults to `True`

## Files Summary

| File | Action |
|------|--------|
| `packages/erkbot/src/erkbot/suggested_replies.py` | NEW |
| `packages/erkbot/src/erkbot/config.py` | MODIFY (1 line) |
| `packages/erkbot/src/erkbot/agent_handler.py` | MODIFY (~15 lines) |
| `packages/erkbot/src/erkbot/slack_handlers.py` | MODIFY (~50 lines) |
| `packages/erkbot/tests/test_suggested_replies.py` | NEW |
| `packages/erkbot/tests/test_agent_handler.py` | MODIFY |
| `packages/erkbot/tests/test_slack_handlers.py` | MODIFY |
| `packages/erkbot/tests/test_config.py` | MODIFY |

## Verification

1. Run unit tests: `make fast-ci` from erkbot package
2. Verify `test_suggested_replies.py` passes (block structure, frozen dataclass)
3. Verify updated `test_agent_handler.py` passes (all 4 existing + 3 new tests)
4. Verify `test_slack_handlers.py` passes (FakeApp supports action, handler registered)
5. Run `ty` for type checking
6. Run `ruff` for linting
