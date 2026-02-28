---
title: ErkBot Agent Configuration
read_when:
  - "working with erkbot configuration"
  - "understanding conditional ErkBot initialization"
  - "adding new erkbot settings"
tripwires:
  - action: "requiring agent config fields in erkbot Settings"
    warning: "Agent config fields (anthropic_api_key, erk_repo_path) must be optional. The bot starts in slack-only mode without them."
---

# ErkBot Agent Configuration

ErkBot uses conditional initialization to support two operational modes: agent-enabled (with Claude SDK) and slack-only (basic Slack commands).

## Configuration

<!-- Source: packages/erkbot/src/erkbot/config.py, Settings -->

`packages/erkbot/src/erkbot/config.py` defines a Pydantic `Settings` class:

- **Required:** `slack_bot_token`, `slack_app_token` (always needed)
- **Optional:** `anthropic_api_key`, `erk_repo_path` (for agent mode), `erk_model`, `max_turns`

Note: Pydantic `Field()` with defaults is an exception to erk's "no default parameters" rule — this applies only to Pydantic config classes.

## Conditional Initialization

<!-- Source: packages/erkbot/src/erkbot/cli.py, _run -->

`packages/erkbot/src/erkbot/cli.py` (`_run` function) implements LBYL validation:

1. Check `anthropic_api_key is not None` AND `erk_repo_path is not None`
2. Validate `repo_path.is_dir()` (LBYL guard)
3. Create `ErkBot` only if all preconditions pass
4. Log structured startup info: `mode=agent-enabled` or `mode=slack-only`

If `erk_repo_path` exists but is not a valid directory, a warning is logged and the bot falls back to slack-only mode.

## System Prompts

<!-- Source: packages/erkbot/src/erkbot/prompts.py -->

`get_erk_system_prompt()` loads the system prompt with LBYL resource loading and supports custom override paths.

## Startup Logging

The bot logs its operational mode at startup using structured format:

- `startup: mode=agent-enabled model=... repo_path=... max_turns=...`
- `startup: mode=slack-only`
