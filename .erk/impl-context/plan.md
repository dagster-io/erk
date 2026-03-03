# Add Progress Indicator During PR Description Generation

## Context

During `erk pr submit` Phase 4 ("Generating PR description") and `erk pr rewrite` Phase 3, the `execute_prompt()` call to Claude CLI blocks for 6-120 seconds with zero visible output, making the command appear hung. The user sees "Analyzing changes with Claude..." then silence until completion.

## Approach

Modify `CommitMessageGenerator.generate()` to run `execute_prompt()` in a background thread, yielding periodic `ProgressEvent` with elapsed time while waiting. This is a single-file change — both `pr submit` and `pr rewrite` consume the generator through `run_commit_message_generation()` which already renders `ProgressEvent` objects.

### Output before:
```
   Analyzing changes with Claude...
   [silence for 6+ seconds]
   PR description generated
```

### Output after:
```
   Analyzing changes with Claude...
   Still waiting... (3s)
   Still waiting... (6s)
   PR description generated
```

## Changes

### `src/erk/core/commit_message_generator.py` (sole file modified)

1. **Add imports**: `import threading` and `import time`
2. **Add constant**: `_PROGRESS_INTERVAL_SECONDS = 3.0`
3. **Add `PromptResult` import**: Extend existing line 17 to `from erk.core.prompt_executor import PromptExecutor, PromptResult`
4. **Replace the synchronous `execute_prompt()` block** (lines 132-167) with a threaded version:
   - Define inner `_run_prompt()` that captures result/exception into holder lists
   - Start as daemon thread
   - Loop on `thread.join(timeout=_PROGRESS_INTERVAL_SECONDS)`, yielding `ProgressEvent(f"Still waiting... ({elapsed}s)")` each interval
   - After thread completes: LBYL check for errors/empty results, then continue with existing result-handling code

### No other files change

- `shared.py` — `render_progress()` and `run_commit_message_generation()` already handle `ProgressEvent`
- `submit_pipeline.py` / `rewrite_cmd.py` — call through `run_commit_message_generation()`, no changes
- `prompt_executor.py` — `execute_prompt()` unchanged
- Tests — `FakePromptExecutor` returns instantly so thread completes before any timer fires; zero extra events yielded; all existing assertions pass

## Verification

1. Run `uv run pytest tests/core/test_commit_message_generator.py` — all existing tests pass unchanged
2. Run `uv run pytest tests/commands/pr/` — PR command tests pass
3. Manual test: `erk pr submit` on a branch with changes — verify "Still waiting..." messages appear during generation
