# Plan: Integration test for stdin ARG_MAX fix

## Context

PR `plnd/fix-stdin-argmax-03-11-0709` changed `ClaudeCliPromptExecutor` to pass prompts via `input=prompt` (stdin) instead of as CLI arguments (`cmd.append(prompt)`). This avoids `ARG_MAX` errors when prompts are large. The change affects two methods:

1. `execute_prompt()` — removed `cmd.append(prompt)`, added `input=prompt`
2. `execute_prompt_passthrough()` — same, plus removed `stdin=subprocess.DEVNULL`, added `text=True`

No integration tests currently exist for `ClaudeCliPromptExecutor`. The existing unit tests cover parsing and pure functions only.

## Approach

Create an integration test that exercises the real subprocess path by substituting a **fake `claude` script** onto PATH. The script reads stdin and echoes it back, allowing us to verify:

1. The prompt arrives via stdin (not as a CLI arg)
2. Large prompts (500KB) that would exceed macOS ARG_MAX (~1MB) work correctly
3. Both `execute_prompt` and `execute_prompt_passthrough` use stdin

### Fake claude script

A minimal Python script placed in `tmp_path`:
- Parses expected flags (`--print`, `--output-format`, `--model`, etc.)
- Reads all of stdin
- Writes it to stdout (simulating `--output-format text` for `execute_prompt`)
- Exits 0

### Test file

`tests/integration/test_prompt_executor_stdin.py`

### Tests

1. **`test_execute_prompt_delivers_prompt_via_stdin`** — Normal-sized prompt, verify round-trip through stdin
2. **`test_execute_prompt_handles_large_prompt_via_stdin`** — 500KB prompt that would fail as CLI arg
3. **`test_execute_prompt_passthrough_delivers_prompt_via_stdin`** — Verify passthrough method also uses stdin (returns exit code 0)

### Fixture

`fake_claude_on_path(tmp_path, monkeypatch)`:
- Writes the fake claude script to `tmp_path / "claude"`
- Makes it executable (`chmod +x`)
- Monkeypatches `PATH` to prepend `tmp_path`
- `build_claude_subprocess_env()` copies from `os.environ`, so monkeypatched PATH propagates to subprocess

## Critical files

- **Modified**: `tests/integration/test_prompt_executor_stdin.py` (new file)
- **Exercised**: `src/erk/core/prompt_executor.py:531-642` (`execute_prompt`, `execute_prompt_passthrough`)
- **Dependency**: `packages/erk-shared/src/erk_shared/subprocess_utils.py:38` (`build_claude_subprocess_env`)

## Verification

```bash
# Run the new integration tests
uv run pytest tests/integration/test_prompt_executor_stdin.py -v

# Verify they're excluded from fast-ci (integration tests are)
make test-integration
```
