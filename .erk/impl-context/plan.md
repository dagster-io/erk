# Plan: Improve `erk one-shot` progress reporting & add timeout to slug generation

## Context

`erk one-shot` takes 1+ minutes to dispatch and provides minimal progress feedback. The CLI shows "Generating branch name..." then goes silent for 30-60s during the haiku LLM subprocess call. Worse, `execute_prompt` (the `subprocess.run` path) has **no timeout**, so if the API stalls, the process hangs forever. The streaming executor (`execute_command_streaming`) already has a 10-minute timeout — `execute_prompt` is the gap.

## Changes

### 1. Add timeout to `execute_prompt` in `ClaudePromptExecutor`

**File:** `src/erk/core/prompt_executor.py`

Add a new constant `PROMPT_TIMEOUT_SECONDS = 120` (2 minutes — generous for a haiku call). Use it in the `subprocess.run` call at line 577. Catch `subprocess.TimeoutExpired` and return a `PromptResult(success=False, ...)`.

```python
PROMPT_TIMEOUT_SECONDS = 120  # 2 minutes for single-shot prompts

# In execute_prompt():
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        env=self._subprocess_env(),
        timeout=PROMPT_TIMEOUT_SECONDS,
    )
except subprocess.TimeoutExpired:
    return PromptResult(
        success=False,
        output="",
        error=f"Prompt execution timed out after {PROMPT_TIMEOUT_SECONDS}s",
    )
```

### 2. Add per-step progress reporting to `dispatch_one_shot`

**File:** `src/erk/cli/commands/one_shot_dispatch.py`

Add completion confirmations and per-step timing for the slow operations. Use `time.monotonic()` for step timing and the existing `format_duration` utility.

Specific additions (dim-styled sub-messages):

| Step | Current output | Add |
|------|---------------|-----|
| Auth check | "Validating GitHub authentication..." | `"  ✓ Authenticated as {username}"` after |
| Skeleton issue | `"  → Plan issue #N"` | Already has completion ✓ |
| Slug generation | "Generating branch name..." | `"  (calling haiku for slug generation...)"` before LLM call, `"  ✓ Slug: {slug} ({elapsed})"` after |
| Branch creation | "Creating branch..." | `"  ✓ Branch created"` after |
| Commit | *(silent)* | `"Committing prompt file..."` before, `"  ✓ Committed"` after |
| Push | "Pushing to remote..." | `"  ✓ Pushed ({elapsed})"` after |
| Draft PR | "Creating draft PR..." | already shows `"  → PR #N"` |
| Workflow trigger | "Triggering one-shot workflow..." | already shows `"  → Run ID: ..."` |

Only time the two known-slow steps (slug generation and push). Use `format_duration` for consistency.

## Files to modify

1. `src/erk/core/prompt_executor.py` — add `PROMPT_TIMEOUT_SECONDS`, add `timeout=` to `subprocess.run`, catch `TimeoutExpired`
2. `src/erk/cli/commands/one_shot_dispatch.py` — add per-step progress messages with timing

## Files NOT modified

- ABC (`packages/erk-shared/src/erk_shared/core/prompt_executor.py`) — no signature change needed, timeout is an implementation detail
- Fake (`packages/erk-shared/src/erk_shared/core/fakes.py`) — no change needed
- Tests (`tests/commands/one_shot/test_one_shot_dispatch.py`) — existing tests continue to pass (output assertions may need minor updates if they check exact output)

## Verification

1. Run existing tests: `pytest tests/commands/one_shot/`
2. Manual: `erk one-shot --dry-run "test prompt"` — verify no regression in dry-run path
3. Manual: `erk one-shot "test prompt"` — verify new progress messages appear with timing
