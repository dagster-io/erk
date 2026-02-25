# Plan: Node 1.7 — Create prompts.py with erk-specific system prompt

**Part of Objective #8036, Node 1.7**

## Context

The erk-slack-bot's agent mode (nodes 1.1–1.6) is functional but uses a hardcoded one-liner system prompt: `"You are erk-bot, an AI assistant for the erk project."` This gives the agent no knowledge of erk commands, workflows, or how to help users. Node 1.7 creates a proper prompts module with an erk-aware system prompt that teaches the agent about plan list, one-shot, objectives, and dash.

## Approach

Follow the established pattern from `erk_shared/gateway/gt/prompts.py`: a `prompts.py` module that loads a markdown prompt file from `resources/`, with an optional custom-prompt override path.

## Files to Create

### 1. `packages/erkbot/src/erkbot/resources/erk_system_prompt.md` (NEW)

System prompt content teaching the agent about:

- **Identity**: You are erk-bot, an AI assistant for the erk project running in Slack
- **Available erk commands** (run via Bash tool in `cwd`):
  - `uv run erk plan list` — list open plans with status
  - `uv run erk one-shot "<message>"` — submit task for remote implementation
  - `uv run erk dash` — show objectives dashboard
  - `uv run erk objective view <number>` — view objective details
- **When to use each command**: decision tree (informational query → respond directly; task requiring code changes → one-shot; status check → plan list or dash)
- **Output formatting**: Keep responses concise for Slack. No markdown headings (Slack doesn't render them). Use plain text, code blocks, and bullet lists.
- **Limitations**: The agent runs with `bypassPermissions` in the repo directory. It can read files and run erk CLI commands but should not make direct code changes (that's what one-shot is for).

### 2. `packages/erkbot/src/erkbot/prompts.py` (NEW)

```python
"""Erk-specific system prompts for erkbot agent."""

from pathlib import Path


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).parent / "resources" / filename
    return prompt_path.read_text(encoding="utf-8")


ERK_SYSTEM_PROMPT = _load_prompt("erk_system_prompt.md")


def get_erk_system_prompt(*, repo_root: Path) -> str:
    custom_prompt_path = repo_root / ".erk" / "prompt-hooks" / "erk-system-prompt.md"
    if custom_prompt_path.exists():
        return custom_prompt_path.read_text(encoding="utf-8")
    return ERK_SYSTEM_PROMPT
```

Pattern: mirrors `erk_shared/gateway/gt/prompts.py:6-30`. `repo_root` is keyword-only, no default.

## Files to Modify

### 3. `packages/erkbot/src/erkbot/cli.py` (MODIFY)

- Add import: `from erkbot.prompts import get_erk_system_prompt`
- Replace hardcoded `system_prompt="You are erk-bot, ..."` with `system_prompt=get_erk_system_prompt(repo_root=repo_path)`
- Lines affected: ~29–35

### 4. `packages/erkbot/tests/test_cli.py` (MODIFY)

- Update `test_run_constructs_erkbot_when_agent_config_present` (line 84–90): the `system_prompt` assertion must change from the hardcoded string to the loaded prompt content
- Add `@patch("erkbot.cli.get_erk_system_prompt")` to mock the prompt function, so the test doesn't depend on prompt file contents
- The mock returns a sentinel string like `"mock-system-prompt"` and the assertion checks `system_prompt="mock-system-prompt"`

## Files to Add (Tests)

### 5. `packages/erkbot/tests/test_prompts.py` (NEW)

Tests:
- `test_erk_system_prompt_loads_from_resources` — verify `ERK_SYSTEM_PROMPT` is a non-empty string containing key phrases (e.g., "erk" and "plan list")
- `test_get_erk_system_prompt_returns_default` — with a `tmp_path` repo_root (no custom file), returns `ERK_SYSTEM_PROMPT`
- `test_get_erk_system_prompt_uses_custom_when_present` — create `.erk/prompt-hooks/erk-system-prompt.md` in `tmp_path`, verify it's returned instead
- `test_erk_system_prompt_mentions_key_commands` — assert the default prompt mentions "plan list", "one-shot", "dash", "objective"

## Implementation Order

1. Create `resources/erk_system_prompt.md` (prompt content)
2. Create `prompts.py` (loading module)
3. Create `tests/test_prompts.py` (prompt tests)
4. Modify `cli.py` (wire in `get_erk_system_prompt`)
5. Modify `tests/test_cli.py` (update assertions)
6. Run tests to verify

## Verification

1. `cd packages/erkbot && uv run pytest tests/test_prompts.py -v` — new prompt tests pass
2. `cd packages/erkbot && uv run pytest tests/test_cli.py -v` — updated CLI tests pass
3. `cd packages/erkbot && uv run pytest tests/ -v` — all erkbot tests pass
4. Verify prompt content reads well and covers the four key areas (plan list, one-shot, objectives, dash)
