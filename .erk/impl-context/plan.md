# Add Progress Feedback to PR Description Generation

## Context

When `erk pr submit` was migrated from invoking Claude CLI subprocess to using direct Anthropic API calls (commit `dccd1b32e`), the progress feedback during the API call was lost. The old implementation used a background thread with periodic "Still waiting... ({elapsed}s)" messages every 3 seconds while the Claude CLI subprocess ran (15+ seconds). The new implementation makes a synchronous `LlmCaller.call()` that blocks for 2-5 seconds with no intermediate feedback.

The user wants the progress feedback restored so they can see that the system is actively working during the API call.

## Current State

The `CommitMessageGenerator.generate()` method (in `src/erk/core/commit_message_generator.py`) yields these progress events:

1. `"Reading diff file..."` (info style)
2. `"Diff loaded ({size} chars)"` (success style)
3. `"Analyzing changes with Claude..."` (info style)
4. **<-- API call blocks here with no feedback -->**
5. `"PR description generated"` (success style)

The gap between events 3 and 5 is where the user sees no output. The API call typically takes 2-5 seconds but could take longer under load.

## Changes

### File: `src/erk/core/commit_message_generator.py`

**What to change:** Restore the background thread + polling pattern so that progress events can be yielded while the API call is in flight.

**Detailed implementation:**

1. Add imports: `import threading` and the Time ABC (`from erk_shared.gateway.time.abc import Time`)
2. Add a module-level constant: `_PROGRESS_INTERVAL_SECONDS = 5.0` (5 seconds, slightly longer than the old 3s since API calls are faster)
3. Update `__init__` to accept `time: Time` parameter (for testability):
   ```python
   def __init__(self, llm_caller: LlmCaller, *, time: Time) -> None:
       self._llm_caller = llm_caller
       self._time = time
   ```
4. In the `generate()` method, after yielding "Analyzing changes with Claude...", replace the direct synchronous call:
   ```python
   result = self._llm_caller.call(user_prompt, system_prompt=system_prompt, max_tokens=4096)
   ```
   with the background thread + polling pattern:
   ```python
   result_holder: list[LlmResponse | NoApiKey | LlmCallFailed] = []
   error_holder: list[Exception] = []

   def _run_call() -> None:
       try:
           result_holder.append(
               self._llm_caller.call(user_prompt, system_prompt=system_prompt, max_tokens=4096)
           )
       except Exception as exc:
           error_holder.append(exc)

   thread = threading.Thread(target=_run_call, daemon=True)
   start_time = self._time.monotonic()
   thread.start()

   while thread.is_alive():
       thread.join(timeout=_PROGRESS_INTERVAL_SECONDS)
       if thread.is_alive():
           elapsed = int(self._time.monotonic() - start_time)
           yield ProgressEvent(f"Still waiting... ({elapsed}s)")

   if error_holder:
       yield CompletionEvent(
           CommitMessageResult(
               success=False,
               title=None,
               body=None,
               error_message=f"LLM call failed: {error_holder[0]}",
           )
       )
       return

   if not result_holder:
       yield CompletionEvent(
           CommitMessageResult(
               success=False,
               title=None,
               body=None,
               error_message="LLM call completed without result",
           )
       )
       return

   result = result_holder[0]
   ```

### File: `src/erk/cli/commands/pr/submit_pipeline.py` (line 655)

**What to change:** Update the `CommitMessageGenerator` construction site to pass `time=ctx.time`.

- Change `CommitMessageGenerator(ctx.llm_caller)` to `CommitMessageGenerator(ctx.llm_caller, time=ctx.time)`

### File: `src/erk/cli/commands/pr/rewrite_cmd.py` (line 125)

**What to change:** Update the `CommitMessageGenerator` construction site to pass `time=ctx.time`.

- Change `CommitMessageGenerator(ctx.llm_caller)` to `CommitMessageGenerator(ctx.llm_caller, time=ctx.time)`

### File: `src/erk/cli/commands/exec/scripts/update_pr_description.py` (line 120)

**What to change:** Update the `CommitMessageGenerator` construction site to pass `time=ctx.time`.

- Change `CommitMessageGenerator(ctx.llm_caller)` to `CommitMessageGenerator(ctx.llm_caller, time=ctx.time)`

### File: `packages/erk-shared/src/erk_shared/gateway/time/abc.py`

**No changes needed.** This file already defines the `Time` ABC with `monotonic()` method. Verify it exists and has the right interface.

### File: `tests/core/test_commit_message_generator.py`

**What to change:** Update all test `CommitMessageGenerator` constructions to pass a `FakeTime` instance.

1. Add import: `from erk_shared.gateway.time.fake import FakeTime`
2. Update all 14 `CommitMessageGenerator(caller)` calls to `CommitMessageGenerator(caller, time=FakeTime())`
   - Lines: 44, 94, 116, 144, 172, 199, 233, 263, 291, 325, 354, 398, 434, 468
3. Add a new test `test_generate_yields_waiting_progress_for_slow_api_call` that:
   - Uses a custom slow FakeLlmCaller (e.g., one that sleeps briefly) combined with FakeTime
   - Asserts that "Still waiting" progress events are emitted during the wait
   - Verifies the final result is still correct

**Verified:** `FakeTime` exists at `packages/erk-shared/src/erk_shared/gateway/time/fake.py:17`. The `Time` ABC is at `packages/erk-shared/src/erk_shared/gateway/time/abc.py:11`. `ErkContext.time: Time` exists at `packages/erk-shared/src/erk_shared/context/context.py:84`.

## Files NOT Changing

- `packages/erk-shared/src/erk_shared/core/llm_caller.py` - LlmCaller ABC stays the same
- `packages/erk-shared/src/erk_shared/core/fakes.py` - FakeLlmCaller stays the same
- `packages/erk-shared/src/erk_shared/gateway/gt/events.py` - ProgressEvent stays the same
- `src/erk/cli/commands/pr/shared.py` - render_progress and run_commit_message_generation stay the same (they already render all ProgressEvents)
- `src/erk/cli/commands/pr/submit_cmd.py` - No changes needed

## Implementation Details

### Why restore threading instead of a simpler approach?

The generator-based event pattern requires yielding progress events from the `generate()` method. A synchronous `LlmCaller.call()` blocks the generator, preventing any yields during the call. Threading is the established pattern in this codebase for this exact purpose (see `docs/learned/architecture/threading-patterns.md` and `docs/learned/architecture/claude-cli-progress.md`).

### Why 5 seconds instead of 3?

The direct API call is faster than the old Claude CLI subprocess (2-5s vs 15+s). A 5-second interval means most successful calls won't even trigger a "Still waiting" message, but slow calls (network issues, API load) will get feedback. The user benefits from knowing the system is alive during unexpected delays.

### Pattern reference

The threading pattern follows the daemon thread + holder list pattern documented in `docs/learned/architecture/threading-patterns.md`. Key elements:
- Daemon thread (won't prevent process exit)
- `result_holder` and `error_holder` lists (thread-safe append)
- `thread.join(timeout=...)` for polling with progress yields
- `self._time.monotonic()` for elapsed time (testable via FakeTime)

### Constructor change impact

The `time: Time` parameter is keyword-only, so all construction sites must be updated:

**Production sites (3):**
- `src/erk/cli/commands/pr/submit_pipeline.py:655`
- `src/erk/cli/commands/pr/rewrite_cmd.py:125`
- `src/erk/cli/commands/exec/scripts/update_pr_description.py:120`

**Test sites (14):**
- `tests/core/test_commit_message_generator.py` - lines 44, 94, 116, 144, 172, 199, 233, 263, 291, 325, 354, 398, 434, 468

All production sites use `time=ctx.time`, all test sites use `time=FakeTime()`.

## Verification

1. Run `pytest tests/core/test_commit_message_generator.py` - all existing tests pass with new constructor
2. Run `pytest tests/commands/pr/test_submit.py` - submit pipeline tests pass
3. Run `ty` for type checking
4. Run `ruff check` for linting
5. Manual verification: run `erk pr submit` on a branch and observe progress output:
   - Should see "Phase 3: Generating PR description"
   - Should see "   Reading diff file..."
   - Should see "   Diff loaded (N chars)"
   - Should see "   Analyzing changes with Claude..."
   - If API takes > 5s, should see "   Still waiting... (5s)"
   - Should see "   PR description generated"