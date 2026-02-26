# Documentation Plan: Add persistent status bar messages for workflow operations

## Context

PR #8270 introduced a significant UX improvement to the ErkDash TUI: replacing ephemeral "starting" toasts with persistent status bar messages for long-running workflow operations. The status bar now tracks multiple concurrent operations with live progress updates from subprocess stdout/stderr, providing continuous visibility until completion.

This implementation established **three major new patterns** for TUI development: (1) multi-operation status bar tracking via a dict-based registry, (2) streaming subprocess execution with real-time progress feedback using `subprocess.Popen`, and (3) a three-phase operation lifecycle for background operations. These patterns are **cross-cutting** (applying to all TUI workflow operations) and **non-obvious** (multiple implementation sessions discovered edge cases and gotchas). Without documentation, future agents will re-learn these patterns through trial and error, as evidenced by the 15+ test failures encountered when callers were missed during signature changes.

The implementation also clarified the relationship between toasts and status bar messages: toasts are for transient feedback on completed actions, while status bar messages provide persistent feedback for ongoing operations. This distinction resolves potential confusion when agents encounter both patterns in the codebase.

## Raw Materials

See session analysis files in `.erk/scratch/sessions/671693c3-da6e-45db-9cb7-8f9ac58de435/learn-agents/`

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 1 (CLARIFIED) |
| Tripwire candidates (score>=4) | 8     |
| Potential tripwires (score2-3) | 7     |

## Documentation Items

### HIGH Priority

#### 1. Multi-Operation Status Bar Tracking Pattern

**Location:** `docs/learned/tui/multi-operation-tracking.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - implementing status bar progress for concurrent TUI operations
  - adding background operation tracking to widgets
  - debugging status bar display issues with multiple operations
tripwires: 3
---

# Multi-Operation Status Bar Tracking

Pattern for tracking multiple concurrent background operations in the TUI status bar without collision.

## Problem

Single-slot message tracking (`_message: str | None`) causes race conditions where concurrent operations overwrite each other's status messages.

## Solution

Use a dict-based registry keyed by operation ID:

- `_operations: dict[str, _OperationState]` tracks all active operations
- `_last_updated_op_id: str | None` tracks which operation was most recently updated
- Display shows most recent operation's progress with `[N ops]` prefix for concurrency

## Pattern Components

The `_OperationState` frozen dataclass in `src/erk/tui/widgets/status_bar.py` captures:
- `label`: Initial operation description (e.g., "Closing plan #123...")
- `progress`: Latest output line from subprocess

The StatusBar widget provides three methods:
- `start_operation(*, op_id: str, label: str)`: Register new operation, add "running" CSS class
- `update_operation(*, op_id: str, progress: str)`: Update latest progress line (LBYL guard for unknown op_id)
- `finish_operation(*, op_id: str)`: Remove operation, clear "running" class if no operations remain

## Display Priority

Three-tier hierarchy in `_update_display()`:
1. Active operations (highest) - show operation progress
2. Transient messages (`set_message()`) - show if no operations
3. Normal status bar content (plan count, timing, hints)

## Usage

See `src/erk/tui/app.py` (grep for `def _start_operation`) for the app-level delegation pattern.
See `src/erk/tui/widgets/status_bar.py` (grep for `def start_operation`) for widget implementation.
```

#### 2. Streaming Subprocess with Progress Updates

**Location:** `docs/learned/tui/streaming-subprocess.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - implementing subprocess calls that need progress feedback
  - migrating from subprocess.run to streaming output
  - adding real-time output display to TUI operations
tripwires: 2
---

# Streaming Subprocess with Progress Updates

Canonical pattern for executing subprocesses with real-time progress feedback in the TUI.

## Problem

`subprocess.run(capture_output=True)` blocks until completion with no visibility. Long-running erk commands (10-60 seconds) leave users uncertain whether the operation is progressing.

## Solution

Use `subprocess.Popen` with line-by-line streaming and thread-safe UI updates.

## Key Configuration

```python
proc = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # CRITICAL: merge streams, erk outputs progress to stderr
    stdin=subprocess.DEVNULL,  # CRITICAL: TUI context, no stdin
    bufsize=1,  # Line-buffered
    text=True,
    cwd=str(repo_root),
)
```

## Line Processing

- Iterate `proc.stdout` line-by-line
- Strip ANSI codes with `click.unstyle(line.rstrip())` before display
- Use `call_from_thread()` to update UI safely from worker thread

## Result Capture

The `_OperationResult` frozen dataclass captures:
- `success: bool` - whether return code was 0
- `output_lines: tuple[str, ...]` - all captured output (immutable)
- `return_code: int` - subprocess exit code

Error extraction uses last non-empty line: `next(reversed(output_lines), "Command failed")`

## Complete Example

See `src/erk/tui/app.py` (grep for `def _run_streaming_operation`) for the full implementation.
```

#### 3. Operation Lifecycle Management

**Location:** `docs/learned/tui/operation-lifecycle.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - implementing new TUI background operations
  - debugging status bar stuck in "running" state
  - adding workflow commands to the TUI
tripwires: 3
---

# Operation Lifecycle Management

Three-phase pattern for TUI background operations with status bar feedback.

## Lifecycle Phases

1. **Start (main thread)**: Generate op_id, call `_start_operation(op_id=op_id, label="...")`
2. **Execute (worker thread)**: Run operation via `@work(thread=True)`, call `_run_streaming_operation()` or similar
3. **Finish (worker thread)**: Call `_finish_operation(op_id)` BEFORE showing completion toast

## Op ID Generation

Pattern: `f"{operation}-{resource_type}-{resource_id}"`

Examples:
- `f"close-plan-{plan_id}"`
- `f"land-pr-{pr_number}"`
- `f"address-remote-{pr_number}"`

CRITICAL: Op ID must be unique per invocation. Never use static strings like `"close-plan"` - collisions occur if operation triggered twice.

## Integration with Existing Patterns

Combines with:
- `@work(thread=True)` decorator for background execution
- `call_from_thread()` for thread-safe UI updates
- `self.notify()` for completion toasts

## Two-Phase Operations

For operations with multiple subprocess calls (e.g., land PR then update objective), reuse the same op_id and call `_update_operation()` between phases to show transition.

See `_land_pr_async` in `src/erk/tui/app.py` for the complete two-phase pattern.

## Error Handling

MUST call `_finish_operation()` in both success and error paths. Pattern:

```python
# Option 1: Explicit branches
if result.success:
    self.call_from_thread(self._finish_operation, op_id=op_id)
    self.call_from_thread(self.notify, "Success!")
else:
    self.call_from_thread(self._finish_operation, op_id=op_id)
    self.call_from_thread(self.notify, "Error: ...", severity="error")
```

Missing cleanup leaves status bar stuck in "running" state permanently.
```

#### 4. Toast vs Status Bar Message Decision Criteria

**Location:** `docs/learned/tui/status-bar-vs-toasts.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - deciding between toast and status bar message
  - implementing user feedback for TUI operations
  - debugging notification visibility issues
tripwires: 1
---

# Toast vs Status Bar Message Decision Criteria

Guidelines for choosing between ephemeral toasts and persistent status bar messages.

## Use Toasts

**Completion events and quick feedback:**
- Success confirmations ("Plan closed successfully")
- Error notifications ("Failed to land PR: merge conflict")
- Quick acknowledgments ("Copied to clipboard")

Characteristics: Auto-dismiss, non-blocking, appropriate for events that need acknowledgment but not ongoing attention.

## Use Status Bar Messages

**Ongoing operations and state changes:**
- In-progress operations ("Closing plan #123...")
- Active filters ("Filtering by stack: feature-branch")
- Mode indicators

Characteristics: Persist until explicitly cleared, always visible, provide continuous feedback.

## Workflow Operation Pattern

Standard pattern for TUI workflow operations:
1. **Start**: Status bar shows operation label
2. **Progress**: Status bar updates with latest subprocess output
3. **Completion**: Status bar cleared, toast shown with result

## Clear Message Pattern

Use `set_message(None)` to clear transient status bar messages.
Use `_finish_operation(op_id)` to clear operation tracking (preferred for workflows).

## Null Guard Pattern

Always guard status bar access: `if self._status_bar is not None:`
```

### MEDIUM Priority

#### 5. Workflow Consistency: Background Operations vs Modals

**Location:** `docs/learned/tui/workflow-consistency.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - adding new workflow commands to TUI
  - deciding between modal screen and background operation
  - refactoring existing modal workflows
---

# Workflow Consistency: Background Operations vs Modals

Design decision for TUI workflow command UX.

## Standard: Background Operations

All workflow commands (address, land, close, dispatch, fix-conflicts) use background operations:
- User stays on current screen
- Status bar shows progress
- Toast on completion

PR #8270 changed fix-conflicts from modal to background operation for consistency.

## When to Use Modals

Modal detail screens are appropriate when:
- Output is long and needs scrolling/review
- User needs to interact with output (copy, search)
- Operation has complex multi-step UI flow

Standard workflow commands rarely need this - their output is captured in status bar and success/failure is reported via toast.

## Pattern Comparison

**Background operation pattern:**
```
User action -> _start_operation -> @work async method -> _finish_operation -> toast
```

**Modal pattern:**
```
User action -> push_screen(DetailScreen) -> DetailScreen runs command -> dismiss
```

See `execute_palette_command` in `src/erk/tui/app.py` for all workflow command implementations.
```

#### 6. Test Pattern: Textual Widget State Inspection

**Location:** `docs/learned/testing/textual-widget-testing.md`
**Action:** CREATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for Textual widgets
  - testing TUI async operations
  - debugging test failures accessing widget internals
tripwires: 2
---

# Test Pattern: Textual Widget State Inspection

How to test Textual widgets without relying on version-specific rendering internals.

## DO: Test Internal State and CSS Classes

```python
# Test internal state
assert status_bar._message == "Expected message"
assert status_bar._operations == {"op-1": _OperationState(...)}

# Test CSS classes
assert status_bar.has_class("running")
assert not status_bar.has_class("running")
```

## DO NOT: Access Rendering Internals

```python
# WRONG - these properties don't exist or are version-specific
str(status_bar.renderable)  # AttributeError
status_bar._content  # Implementation detail
```

## Async Worker Test Pattern

For testing `@work(thread=True)` methods:

1. Monkeypatch `subprocess.Popen` with `_FakePopen`
2. Call async method directly
3. `await pilot.pause(0.3)` for worker completion
4. Assert observable state

See `TestOperationTracking` in `tests/tui/test_app.py` for complete examples.

## FakePopen Helper

Create a `_FakePopen` class that:
- Has `stdout` attribute yielding configurable output lines
- Has `wait()` method returning configurable return code
- Matches `subprocess.Popen` interface for monkeypatching
```

#### 7. Two-Phase Operation Example

**Location:** `docs/learned/tui/operation-lifecycle.md` (add section)
**Action:** UPDATE
**Source:** [Impl] [PR #8270]

**Draft Content:**

Add section to operation-lifecycle.md:

```markdown
## Two-Phase Operation: Land PR Example

The `_land_pr_async` method demonstrates handling operations with multiple subprocess calls using a single op_id:

1. Start with `_start_operation(op_id=op_id, label="Landing PR #N...")`
2. Execute first subprocess (land PR)
3. On success, call `_update_operation(op_id=op_id, progress="Updating objective #M...")` to show transition
4. Execute second subprocess (update objective)
5. Finish with `_finish_operation(op_id=op_id)` then show toast

Key insight: Don't create a new op_id for the second phase. Reuse the same ID and update progress to show continuous operation flow.

See `src/erk/tui/app.py` (grep for `def _land_pr_async`) for the complete implementation.
```

### LOW Priority

#### 8. Learn Materials Branch Convention

**Location:** `docs/learned/documentation/learn-branch-convention.md`
**Action:** CREATE
**Source:** [PR #8270]

**Draft Content:**

```markdown
---
read-when:
  - creating learn documentation from PR analysis
  - linking documentation to source implementations
---

# Learn Materials Branch Convention

Workflow for linking PRs to learn documentation branches.

## Convention

Create branch named `learn/{pr_number}` for documentation generated from PR analysis.

## Purpose

Enables bidirectional tracking:
- From implementation PR -> find associated learn materials
- From learn branch -> find source implementation

## Workflow

1. Analyze PR via `/erk:learn <pr-number>`
2. Learn pipeline creates `learn/{pr_number}` branch
3. Post branch name as comment on original PR
```

### SHOULD_BE_CODE Items

#### 9. `next(reversed(...))` Pattern for LBYL

**Action:** CODE_CHANGE
**Location:** `src/erk/tui/app.py` in `_run_streaming_operation()` method

Add docstring or comment explaining the pattern:

```python
# Extract last non-empty line as error message using LBYL-compliant pattern
# next(reversed(seq), default) efficiently gets last element without try/except
error_msg = next(reversed(output_lines), "Command failed")
```

This is a dignified alternative to `output_lines[-1] if output_lines else "default"` or try/except for IndexError.

#### 10. Status Bar Display Priority Logic

**Action:** CODE_CHANGE
**Location:** `src/erk/tui/widgets/status_bar.py` in `_update_display()` method

Add docstring explaining the three-tier priority:

```python
def _update_display(self) -> None:
    """Update the status bar display.

    Display priority (highest to lowest):
    1. Active operations - show progress with [N ops] prefix if multiple
    2. Transient message - show if set and no operations active
    3. Normal content - plan count, timing, hints
    """
```

## Contradiction Resolutions

### 1. Toast vs Status Bar Usage Pattern

**Existing doc:** `docs/learned/tui/async-action-refresh-pattern.md`
**Conflict:** Documentation mentions "Show success toast" but PR #8270 introduced status bar for in-progress operations

**Resolution:** CLARIFY_CONTEXT - Both patterns are valid for different use cases:
- Toasts for completed actions (no change to existing docs)
- Status bar messages for ongoing operations (new documentation)

**Action Required:**
1. Create `docs/learned/tui/status-bar-vs-toasts.md` (item #4 above)
2. Add cross-reference from `async-action-refresh-pattern.md` noting that in-progress feedback uses status bar, completion uses toasts

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing Callers After Signature Change

**What happened:** Changed async method signatures in `app.py` to add `op_id` parameter, but 15 tests failed because callers in `plan_detail_screen.py` weren't updated.

**Root cause:** Signature changes require updating ALL callers, not just those in the same file.

**Prevention:** After changing async method signatures, grep for method name across entire `src/erk/tui/` directory to find all callers.

**Recommendation:** TRIPWIRE - Score 7 (Non-obvious +2, Cross-cutting +2, Destructive +2, Repeated +1)

### 2. Test Monkeypatch Mismatch

**What happened:** Tests monkeypatched `subprocess.run` but implementation migrated to `subprocess.Popen`, causing 20+ test failures.

**Root cause:** Test infrastructure wasn't updated alongside production code migration.

**Prevention:** When migrating subprocess calls, search test files for method names being changed and update monkeypatches simultaneously.

**Recommendation:** TRIPWIRE - Score 6 (Non-obvious +2, Cross-cutting +2, Destructive +2)

### 3. Second Operation Overwrites First's Status

**What happened:** Single `str | None` slot couldn't track concurrent operations - second operation would overwrite first's message.

**Root cause:** Design assumption of sequential operations was invalid.

**Prevention:** Use dict-based registry keyed by operation ID for any multi-operation tracking.

**Recommendation:** ADD_TO_DOC - Covered in multi-operation-tracking.md

### 4. UI Updates Invisible During Modal Transitions

**What happened:** Status bar updates during `push_screen()` dismissal weren't visible due to render cycle timing.

**Root cause:** Widget updates scheduled during screen transitions may not display properly.

**Prevention:** For timing-sensitive feedback after modal dismissal, use dedicated notification mechanisms or ensure the update completes before transition.

**Recommendation:** CONTEXT_ONLY - Addressed by switching to background operation pattern

### 5. Missing Message Clear on Operation Failure

**What happened:** `_fix_conflicts_remote_async` never cleared the status bar message on completion, leaving it stuck.

**Root cause:** Manual cleanup easily forgotten in error handlers.

**Prevention:** Operation lifecycle pattern with explicit `_finish_operation` call ensures cleanup in all paths.

**Recommendation:** TRIPWIRE - Covered by "Always finish operations" tripwire

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Always Finish Operations

**Score:** 8/10 (Non-obvious: +2, Cross-cutting: +2, Silent failure: +2, Destructive potential: +2)
**Trigger:** Before implementing TUI background operations
**Warning:** MUST call `_finish_operation()` in both success and error paths before showing completion toasts. Missing this leaves status bar stuck in "running" state permanently.
**Target doc:** `docs/learned/tui/tripwires.md`

This is the most critical tripwire from this implementation. Multiple sessions encountered this issue, and the fix isn't obvious - you must finish the operation even when showing an error toast.

### 2. Merge stdout and stderr for Subprocess Progress

**Score:** 6/10 (Non-obvious: +2, External tool quirk: +1, Cross-cutting: +2, Silent failure: +1)
**Trigger:** Before using subprocess.Popen for progress updates
**Warning:** MUST use `stderr=subprocess.STDOUT` to merge streams. Many erk commands output progress to stderr (not stdout), so separate streams would miss progress messages.
**Target doc:** `docs/learned/tui/tripwires.md`

Discovered in session 321612bf - without merged streams, progress updates from stderr-heavy commands are invisible.

### 3. Op ID Must Be Unique Per Invocation

**Score:** 6/10 (Non-obvious: +2, Silent failure: +2, Destructive potential: +2)
**Trigger:** Before generating operation IDs
**Warning:** MUST include resource ID in `op_id` (e.g., `f"close-plan-{plan_id}"`). DO NOT use static strings like `"close-plan"` - would collide if triggered twice. Pattern: `f"{operation}-{resource_type}-{resource_id}"`
**Target doc:** `docs/learned/tui/tripwires.md`

Static op_ids cause silent overwrite when user triggers the same operation type twice.

### 4. Update All Callers After Async Method Signature Changes

**Score:** 7/10 (Non-obvious: +2, Cross-cutting: +2, Destructive potential: +2, Repeated pattern: +1)
**Trigger:** After changing signatures of @work(thread=True) methods
**Warning:** Check both `execute_palette_command` in `app.py` AND command handlers in `plan_detail_screen.py`. Grep for method name across entire `src/erk/tui/` directory to find all callers.
**Target doc:** `docs/learned/tui/tripwires.md`

Session 94c709f6-part3 discovered 15 test failures from this exact pattern - callers in plan_detail_screen.py were missed.

### 5. Test Monkeypatch Mismatch After Subprocess Migration

**Score:** 6/10 (Non-obvious: +2, Cross-cutting: +2, Destructive potential: +2)
**Trigger:** After migrating from subprocess.run to subprocess.Popen
**Warning:** Update test monkeypatches from `subprocess.run` to `subprocess.Popen`. Create `_FakePopen` helper class with `stdout` iterator and `wait()` method.
**Target doc:** `docs/learned/testing/tripwires.md`

20+ test failures occurred because tests still monkeypatched `subprocess.run` after migration.

### 6. ANSI Stripping for TUI Display

**Score:** 4/10 (Non-obvious: +2, Cross-cutting: +2)
**Trigger:** Before displaying subprocess output in Textual widgets
**Warning:** MUST strip ANSI codes using `click.unstyle()` before displaying in plain text widgets. Raw ANSI codes cause visual corruption.
**Target doc:** `docs/learned/tui/tripwires.md`

Standard requirement for any subprocess output displayed in TUI.

### 7. Status Bar Null Guards

**Score:** 4/10 (Cross-cutting: +2, Silent failure: +2)
**Trigger:** Before accessing self._status_bar
**Warning:** MUST use guard clause `if self._status_bar is not None:`. Status bar may be None in tests or during initialization.
**Target doc:** `docs/learned/tui/tripwires.md`

Defensive programming pattern required for all status bar interactions.

### 8. Missing Cleanup in Async Operations (Subsumed by #1)

**Score:** 5/10 (Silent failure: +2, Destructive potential: +2, Repeated pattern: +1)
**Trigger:** Before implementing @work(thread=True) methods
**Warning:** Ensure cleanup code (finish_operation, notify) runs in both success and error paths.
**Target doc:** `docs/learned/tui/tripwires.md`

Subsumed by tripwire #1 but worth mentioning as a general async pattern.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Pre-existing Test Failures

**Score:** 3/10 (Repeated pattern, Silent failure)
**Notes:** Before starting implementation, run tests and note pre-existing failures. Use `git stash` to verify if unsure. Deselect pre-existing failures for faster iteration. Would promote if more sessions encounter this confusion.

### 2. Edit Context Uniqueness

**Score:** 2/10 (Repeated pattern)
**Notes:** When Edit tool fails with "Found N matches", add 1-2 lines of surrounding context rather than trying different substrings. Common pattern but well-understood.

### 3. Modal Dismissal UI Updates

**Score:** 3/10 (Non-obvious, Cross-cutting)
**Notes:** Status bar updates during modal transitions may not display. Resolved by moving to background operation pattern rather than documenting the edge case.

### 4. LaunchScreen Flicker

**Score:** 2/10 (Non-obvious)
**Notes:** Two-keystroke flows (l + l for land) cause brief visual flicker as modal appears and disappears quickly. UX issue but not a code correctness concern.

### 5. Task Tool vs Skill Invocation

**Score:** 3/10 (Non-obvious, External tool quirk)
**Notes:** For pr-feedback-classifier in pr-address workflow, use Task tool instead of Skill tool. The skill's `context: fork` metadata doesn't create true subagent isolation in `--print` mode. Specific to one command, may not generalize.

### 6. Concurrent Operation Overwrites (Fixed)

**Score:** 3/10 (Silent failure, Destructive potential)
**Notes:** This was FIXED by PR #8270 - single message slot replaced with dict registry. Documenting for historical context but no longer a tripwire.

### 7. User Terminology Misalignment

**Score:** 2/10 (Repeated pattern)
**Notes:** "fix tests" often means "fix CI failures" even when tests pass. Parse CI output to identify actual failure stage. General communication pattern.

## Cross-References to Add

After implementing documentation items:

1. From `docs/learned/tui/async-action-refresh-pattern.md` -> Link to `status-bar-vs-toasts.md` and `operation-lifecycle.md`
2. From `docs/learned/tui/dual-handler-pattern.md` -> Link to `status-bar-vs-toasts.md` for clarity on contexts
3. From `docs/learned/tui/streaming-output.md` -> Link to `streaming-subprocess.md` for multi-operation enhancement
4. From `docs/learned/testing/tripwires.md` -> Link to new tripwires in `docs/learned/tui/tripwires.md`
5. Add new TUI tripwires (8 items) to `docs/learned/tui/tripwires.md`
