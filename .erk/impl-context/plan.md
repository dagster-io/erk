# Plan: Fall back to Claude CLI when ANTHROPIC_API_KEY is unavailable

## Context

When `erk pr submit` generates PR descriptions, it uses `AnthropicLlmCaller` which calls the Anthropic API directly for speed. If `ANTHROPIC_API_KEY` is not set, it returns `NoApiKey`, which propagates as an error. This blocks PR description generation even though the user is running inside Claude Code, which has its own authentication. The fix: fall back to invoking `claude --print` as a subprocess when the API key isn't available.

## Changes

### 1. Add Claude CLI fallback in `src/erk/core/fast_llm.py`

When `ANTHROPIC_API_KEY` is not set, instead of returning `NoApiKey`, invoke `claude --print` with the prompt via subprocess:

- Check `shutil.which("claude")` to confirm CLI is available
- If not available, return `NoApiKey` as before (true dead end)
- If available, run `claude --print --no-session-persistence --model claude-haiku-4-5-20251001 --output-format text --system-prompt <system_prompt> <prompt>` via `subprocess.run`
- Use `build_claude_subprocess_env()` for the env (same as `ClaudePromptExecutor`)
- On success, return `LlmResponse(text=...)`
- On failure, return `LlmCallFailed(message=...)`
- Log a debug message noting the fallback

### 2. Update tests in `tests/core/test_fast_llm.py`

- Update `test_anthropic_llm_caller_returns_no_api_key_without_env` — it should now only return `NoApiKey` when both the API key is missing AND `claude` CLI is unavailable
- Add test: no API key + claude available → falls back to CLI (mock `subprocess.run` and `shutil.which`)
- Add test: no API key + claude not available → returns `NoApiKey`

## Files to modify

- `src/erk/core/fast_llm.py` — add CLI fallback logic
- `tests/core/test_fast_llm.py` — update and add tests

## Verification

- Run `uv run pytest tests/core/test_fast_llm.py` to verify tests pass
- Run `uv run ty check src/erk/core/fast_llm.py` for type checking
