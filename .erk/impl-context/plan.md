# Plan: Add tests for app.py, cli.py, and config.py

## Context

PR review bots flagged 3 files in `packages/erk-slack-bot/` lacking test coverage. The source files are simple (config dataclass, app factory, CLI entry point), so the tests are straightforward. Existing tests in the package use `unittest.TestCase` + `unittest.mock`.

## Files to create

- `packages/erk-slack-bot/tests/test_config.py`
- `packages/erk-slack-bot/tests/test_app.py`
- `packages/erk-slack-bot/tests/test_cli.py`

## Implementation

### Phase 1: test_config.py

Test the `Settings` pydantic-settings class (`config.py`).

3 tests:
1. **test_settings_from_env_vars** — `Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")`, assert `slack_bot_token == "x"` and `slack_app_token == "y"`
2. **test_settings_defaults** — Construct with required tokens, assert default values: `max_slack_code_block_chars == 2800`, `max_one_shot_message_chars == 1200`, `one_shot_progress_tail_lines == 40`, `one_shot_progress_update_interval_seconds == 1.0`, `one_shot_failure_tail_lines == 60`, `one_shot_timeout_seconds == 900.0`
3. **test_settings_missing_required_raises** — `Settings()` with no args raises `pydantic.ValidationError`

### Phase 2: test_app.py

Test the `create_app()` factory (`app.py`).

1 test:
1. **test_create_app_returns_app_with_handlers** — Patch `slack_bolt.App` and `erk_slack_bot.app.register_handlers`. Call `create_app(settings=settings)`. Assert `App` was constructed with `token=settings.slack_bot_token` and `register_handlers` was called with the app instance and `settings=settings`.

### Phase 3: test_cli.py

Test the `main()` entry point (`cli.py`).

1 test:
1. **test_main_wires_app_and_starts_handler** — Patch `erk_slack_bot.cli.load_dotenv`, `erk_slack_bot.cli.Settings`, `erk_slack_bot.cli.create_app`, and `erk_slack_bot.cli.SocketModeHandler`. Call `main()`. Assert: `load_dotenv()` called, `Settings()` called, `create_app(settings=mock_settings)` called, `SocketModeHandler(mock_app, mock_settings.slack_app_token).start()` called.

## Verification

```bash
uv run --package erk-slack-bot pytest packages/erk-slack-bot/tests/ -v
```
