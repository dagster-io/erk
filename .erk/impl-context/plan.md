# Plan: Make `erk pr address` launch Claude interactively

## Context

Currently `erk pr address` runs Claude non-interactively via `stream_command_with_feedback()`, which streams output but doesn't allow user interaction. The user wants it to launch Claude interactively (replacing the current process with `os.execvp`), matching the pattern used by `erk pr replan` and `erk objective plan`.

## Changes

### 1. Rewrite `src/erk/cli/commands/pr/address_cmd.py`

Replace the `stream_command_with_feedback` approach with `ctx.agent_launcher.launch_interactive()`, following the `replan_cmd.py` pattern:

- Remove `stream_command_with_feedback` import and `prompt_executor` usage
- Load `InteractiveAgentConfig` from `ctx.global_config.interactive_agent` (with `InteractiveAgentConfig.default()` fallback)
- Map `--dangerous`/`--safe` flags to config overrides:
  - `--dangerous` → `dangerous_override=True`
  - `--safe` → `permission_mode_override="safe"`, no dangerous override
  - Default (neither flag) → use config defaults with `allow_dangerous_override=True` when `live_dangerously` is true
- Use `config.with_overrides(permission_mode_override="edits", ...)` to set the permission mode (edits mode, matching current behavior)
- Call `ctx.agent_launcher.launch_interactive(config, command="/erk:pr-address")`
- Wrap in try/except RuntimeError for CLI not installed errors

### 2. Rewrite `tests/commands/pr/test_address.py`

Replace `FakePromptExecutor`-based tests with `FakeAgentLauncher`-based tests, following `test_replan.py` pattern:

- Test: launches with correct command (`/erk:pr-address`) and permission mode (`edits`)
- Test: `--dangerous` flag sets `dangerous=True` on config
- Test: `--safe` flag overrides to safe permission mode
- Test: `--dangerous` + `--safe` is mutually exclusive error
- Test: error when agent CLI not installed (`launch_error` on FakeAgentLauncher)

## Files to modify

- `src/erk/cli/commands/pr/address_cmd.py` — rewrite command implementation
- `tests/commands/pr/test_address.py` — rewrite tests for new pattern

## Verification

- Run `uv run pytest tests/commands/pr/test_address.py` to verify tests pass
- Run `uv run ruff check src/erk/cli/commands/pr/address_cmd.py` for lint
- Run `uv run ty check src/erk/cli/commands/pr/address_cmd.py` for type check
