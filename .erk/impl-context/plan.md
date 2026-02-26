# Documentation Plan: Add async learn triggering to TUI land workflow

## Context

This documentation plan captures insights from implementing async learn triggering in the TUI's "Land PR" action (PR #8275). Previously, plans landed via the interactive dashboard (`erk dash -i`) silently skipped learn workflows, while the CLI path (`erk land`) automatically triggered them. This created a gap where implementation insights from TUI-landed PRs were lost.

The fix adds async learn triggering as a third sequential step after land and objective-update in the TUI. The implementation uses fire-and-forget semantics (non-blocking), shows warnings rather than errors on failure (since the primary land succeeded), and reuses the CLI's `trigger-async-learn` exec script for consistency. The decision logic for when to trigger learn mirrors the CLI's `_check_learn_status_and_prompt` function, creating a TUI-CLI parity requirement that must be maintained going forward.

Documentation matters here because: (1) the sequential chaining pattern for multi-step background operations is architectural and will be reused; (2) the TUI-CLI synchronization requirement is non-obvious and creates a cross-cutting tripwire; (3) several testing patterns emerged that apply beyond this specific feature.

## Raw Materials

PR #8275 implementation sessions and review feedback.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 23    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. TUI-CLI learn trigger synchronization

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## TUI-CLI Learn Trigger Synchronization

**TRIPWIRE**: Before modifying learn trigger logic in TUI or CLI

Changes to `_should_trigger_learn` in `src/erk/tui/app.py` require updating `_check_learn_status_and_prompt` in `src/erk/cli/commands/land_cmd.py` and vice versa. The two functions must stay synchronized - they implement the same decision logic for determining when async learn workflows should trigger after landing a PR.

**Skip conditions (must be identical in both paths):**
- Plan is itself a learn plan (`is_learn_plan=True`)
- Learn already in terminal state: `completed_no_plan`, `completed_with_plan`, `plan_completed`, `pending`

See `src/erk/tui/app.py` (grep for `_should_trigger_learn`) and `src/erk/cli/commands/land_cmd.py` (grep for `_check_learn_status_and_prompt`).
```

---

#### 2. Bot duplicate feedback handling

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Bot Duplicate Feedback Handling

**TRIPWIRE**: When addressing bot review comments

GitHub Apps that post automated reviews often create BOTH a review thread (inline comment) AND a discussion comment (top-level PR comment) about the same issue. Both require explicit handling:

1. Resolve the review thread via `erk exec resolve-review-threads`
2. Reply to the discussion comment via `erk exec reply-to-discussion-comment`

Thread resolution alone does NOT close or acknowledge the discussion comment. The discussion comment serves as a summary/notification, while the review thread is the actionable inline feedback.

**Example**: Test Coverage Review bot posts inline feedback on a specific line AND a top-level summary comment. After resolving the inline thread, you must also reply to the summary comment.
```

---

#### 3. Pre-existing format violations blocking PR address

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Pre-existing Format Violations

**TRIPWIRE**: Before starting PR address workflow

Pre-existing formatting violations in test files can block CI when addressing unrelated review comments. Before starting the PR address workflow:

1. Run `make fast-ci` or `ruff format --check tests/` to identify violations
2. Fix formatting issues proactively in a separate commit before addressing review comments
3. This prevents the frustrating pattern of: make review fix → CI fails on formatting → fix formatting → re-run CI

Format debt in test files is especially common because test assertions and mock calls often span multiple lines.
```

---

#### 4. Sequential background operations pattern

**Location:** `docs/learned/tui/sequential-background-operations.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Architectural pattern for chaining multiple sequential background operations in TUI
read-when:
  - implementing multi-step TUI operations
  - adding steps to existing background operations
  - working with `@work(thread=True)` workers
---

# Sequential Background Operations

This document describes the architectural pattern for chaining multiple sequential background operations in the TUI.

## Core Pattern

Multi-step TUI operations (like land → objective-update → learn-trigger) run sequentially within a single `@work(thread=True)` worker. Each step:

1. Runs to completion before the next step starts
2. Reports progress via `_update_operation()`
3. Can be conditional on metadata or previous step results
4. Uses streaming operations (`_run_streaming_operation`) for subprocess calls

See `src/erk/tui/app.py` (grep for `_land_pr_async`) for the canonical example.

## Error Severity Decisions

**Primary operation success determines severity for secondary failures:**
- If land succeeds but objective-update fails → warning
- If land succeeds but learn-trigger fails → warning
- If land fails → error

This pattern ensures users know their main action succeeded even if auxiliary steps fail.

## When to Use Sequential vs Parallel

**Sequential** (current pattern): When steps have state dependencies - each step depends on the previous step's success or modifies state the next step reads.

**Parallel**: When steps are truly independent. Currently not used in TUI operations, but could be implemented for operations like "refresh multiple worktree statuses."

## Adding New Steps

When adding a step to an existing sequential operation:

1. Add conditional check (e.g., `if _should_trigger_learn(...)`)
2. Update operation progress message
3. Use `_run_streaming_operation` for subprocess calls
4. Handle failure with appropriate severity (usually warning if primary succeeded)
5. Add tests for: happy path, skip condition, failure isolation

## Related Documentation

- Error extraction: `_last_output_line` helper in same file
- Streaming operations: `_run_streaming_operation` pattern
- Background workers: `docs/learned/tui/async-action-refresh-pattern.md`
```

---

#### 5. TUI async learn triggering implementation

**Location:** `docs/learned/tui/land-learn-integration.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Complete guide to TUI async learn triggering after landing PRs
read-when:
  - modifying TUI land operation behavior
  - debugging learn workflow not triggering from TUI
  - understanding TUI-CLI learn parity
---

# TUI Async Learn Triggering

This document describes how the TUI triggers async learn workflows after landing PRs.

## Overview

The TUI's "Land PR" action triggers async learn as a fire-and-forget operation. Unlike the CLI, the TUI doesn't block or prompt - it triggers the learn workflow and immediately returns control.

## Decision Logic

The `_should_trigger_learn` function determines eligibility. See `src/erk/tui/app.py` for implementation.

**Triggers when:**
- Plan is NOT a learn plan itself
- Learn status is NOT in a terminal state (`completed_no_plan`, `completed_with_plan`, `plan_completed`, `pending`)

**Why no ErkContext access:** The TUI doesn't have access to ErkContext or session lookups. It relies on metadata from the plan backend (`is_learn_plan`, `learn_status` fields). The exec script handles edge cases like "no sessions found" gracefully.

## Execution Flow

1. Land PR via `erk exec land-execute`
2. Update objective (if applicable)
3. Check `_should_trigger_learn(is_learn_plan, learn_status)`
4. If eligible: call `erk exec trigger-async-learn <plan_id>`
5. Show success toast or warning on failure

## Failure Handling

Learn failures show as **warnings**, not errors, because:
- The primary land operation succeeded
- Users should know their main action completed
- Learn is auxiliary - its failure doesn't invalidate the land

## TUI-CLI Parity

The TUI's `_should_trigger_learn` must stay synchronized with CLI's `_check_learn_status_and_prompt`. Changes to one require updating the other. See tripwire in `docs/learned/planning/tripwires.md`.

## Testing

See `tests/tui/test_app.py`:
- `TestShouldTriggerLearn` - unit tests for decision logic
- `test_land_pr_chains_learn_trigger` - integration test for happy path
- `test_land_pr_skips_learn_for_learn_plan` - skip condition for learn plans
- `test_land_pr_skips_learn_when_already_completed` - terminal state detection
- `test_land_pr_learn_failure_does_not_affect_land` - failure isolation
```

---

#### 6. Warning vs error severity for chained operations

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Chained Operation Error Severity

**TRIPWIRE**: When implementing multi-step chained background operations in TUI

Primary operation success determines severity for subsequent failures:
- Primary succeeds + secondary fails = **warning** (not error)
- Primary fails = **error**

**Rationale**: Users need to know their main action completed successfully. Auxiliary failures (like learn triggering after a successful land) are important to surface but shouldn't alarm users about their primary goal.

**Example**: Land succeeds, learn trigger fails → show warning toast "Learn workflow failed to start" rather than error banner.

See `src/erk/tui/app.py` (grep for `_land_pr_async`) for severity assignment pattern.
```

---

### MEDIUM Priority

#### 7. Subprocess test pattern migration (run to Popen)

**Location:** `docs/learned/testing/tui-async-testing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Testing patterns for TUI async operations using subprocess.Popen
read-when:
  - writing tests for TUI background operations
  - debugging TUI test failures with subprocess mocks
  - migrating tests from subprocess.run to Popen
---

# TUI Async Operation Testing

This document covers testing patterns for TUI operations that use streaming subprocess calls.

## Why Popen, Not Run

Production TUI code uses `_run_streaming_operation()` which calls `subprocess.Popen` for real-time output streaming. Tests must mock `Popen`, not `run`, to match the production execution path.

**Wrong:**
```python
def fake_run(args, **kwargs):
    return subprocess.CompletedProcess(args, 0)
monkeypatch.setattr(subprocess, "run", fake_run)
```

**Correct:**
```python
def fake_popen(*args, **kwargs):
    return _FakePopen(lines=("Success",), return_code=0)
monkeypatch.setattr(subprocess, "Popen", fake_popen)
```

## Using _FakePopen

The `_FakePopen` class in `tests/tui/test_app.py` simulates streaming output. It provides:
- `stdout.readline()` - returns lines one at a time
- `poll()` - returns None while lines remain, then return_code
- `returncode` - final exit code

See `tests/tui/test_app.py` (grep for `_FakePopen`) for implementation and usage examples.

## Testing Multiple Operations

For chained operations (land → objective → learn), your fake Popen must handle multiple subprocess calls:

```python
call_count = 0
def fake_popen(*args, **kwargs):
    nonlocal call_count
    call_count += 1
    if call_count == 1:  # land
        return _FakePopen(lines=("Landed PR",), return_code=0)
    elif call_count == 2:  # objective
        return _FakePopen(lines=("Updated",), return_code=0)
    # etc.
```

## Failure Isolation Testing

Test that secondary operation failures don't break the primary operation:

1. Mock primary to succeed
2. Mock secondary to fail (return_code=1)
3. Assert primary result is success
4. Assert warning message appears (not error)
```

---

#### 8. TUI learn triggering test patterns

**Location:** `docs/learned/testing/tui-test-patterns.md`
**Action:** UPDATE (or CREATE if doesn't exist)
**Source:** [Impl]

**Draft Content:**

```markdown
## TUI Learn Triggering Tests

### Test Structure

TUI learn triggering uses a layered test approach:

1. **Unit tests** (`TestShouldTriggerLearn`): Pure function tests for decision logic
2. **Integration tests**: Full operation chaining with mocked subprocesses
3. **Edge case tests**: Learn plans, terminal states, missing metadata
4. **Failure isolation tests**: Secondary failures don't break primary

### Unit Testing Decision Logic

Extract decision logic to pure functions outside the App class, then test directly:

```python
class TestShouldTriggerLearn:
    def test_triggers_when_eligible(self) -> None:
        assert _should_trigger_learn(is_learn_plan=False, learn_status=None)

    def test_skips_for_learn_plan(self) -> None:
        assert not _should_trigger_learn(is_learn_plan=True, learn_status=None)
```

### Integration Test Pattern

See `tests/tui/test_app.py` for examples of:
- `test_land_pr_chains_learn_trigger` - verifies command sequence
- `test_land_pr_learn_failure_does_not_affect_land` - failure isolation

### Test File Location

TUI async operation tests live in `tests/tui/test_app.py`. Decision logic unit tests should be at the top of the file, grouped by function name.
```

---

#### 9. Ruff multi-line formatting cascade

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Ruff Multi-line Formatting

**TRIPWIRE**: When editing test files with multi-line function calls

Ruff enforces one-argument-per-line when function calls span multiple lines. This applies even if individual lines don't exceed the line length limit.

**The cascade pattern**: Fixing one formatting issue can expose additional issues in related code. Run `ruff format --diff` after edits to catch ALL formatting issues before CI, not just the immediate line you changed.

**Common triggers in test files:**
- Adding parameters to mock function calls
- Modifying assertion statements with multiple arguments
- Editing list literals that span lines

**Prevention**: After any test file edit, run `ruff format --diff tests/` to see the complete picture before running CI.
```

---

#### 10. Textual catch-all key handler testing

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Textual Catch-All Key Handler Testing

**TRIPWIRE**: When testing Textual `on_key()` handlers that consume all input

Test with arbitrary keys NOT in BINDINGS to verify catch-all behavior:

**Wrong approach**: Only testing bound keys (escape, q, space) doesn't verify the handler catches ALL keys.

**Correct approach**: Press keys that are NOT in the screen's BINDINGS list:
```python
# If BINDINGS only has escape/q/space, test with 'x':
await pilot.press("x")  # arbitrary key not in bindings
assert app.query_one(MyScreen).is_closed
```

This ensures the `on_key()` method truly catches arbitrary input, not just the explicitly bound dismiss keys.

See `tests/tui/test_app.py` (grep for `test_issue_body_screen_dismisses_on_arbitrary_key`) for example.
```

---

#### 11. Error extraction DRY pattern

**Location:** `docs/learned/tui/async-action-refresh-pattern.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section:

```markdown
## Error Message Extraction

Use `_last_output_line()` helper for extracting error messages from `_OperationResult`:

```python
error_msg = _last_output_line(result)  # Returns last non-empty line or "Unknown error"
```

**Before** (repeated 9 times):
```python
error_msg = next((ln for ln in reversed(result.output_lines) if ln), "Unknown error")
```

**After** (single helper):
```python
def _last_output_line(result: _OperationResult) -> str:
    return next((ln for ln in reversed(result.output_lines) if ln), "Unknown error")
```

All async operations should use this helper for consistent error extraction. See `src/erk/tui/app.py` (grep for `_last_output_line`).
```

---

#### 12. Learn workflow TUI integration

**Location:** `docs/learned/planning/learn-pipeline-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section:

```markdown
## TUI Trigger Point

The TUI triggers learn via `erk exec trigger-async-learn <plan_id>` as part of the "Land PR" action. This is a fire-and-forget operation - the TUI doesn't block waiting for learn to complete.

**Data flow:**
1. TUI checks eligibility via `_should_trigger_learn()`
2. TUI calls `erk exec trigger-async-learn <plan_id>`
3. Exec script performs local preprocessing (session discovery, compression)
4. Exec script triggers `learn.yml` GitHub Actions workflow
5. TUI shows toast and returns immediately

**Why local preprocessing**: Avoids ~30s CI startup overhead. The expensive work (session compression, XML conversion) happens locally before handing off to GitHub Actions.

See `src/erk/tui/app.py` (grep for `_land_pr_async`) for TUI integration and `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` for the exec script.
```

---

#### 13. Testing behavior changes explicitly

**Location:** `docs/learned/testing/behavior-change-testing.md`
**Action:** CREATE
**Source:** [PR #8275]

**Draft Content:**

```markdown
---
description: Guidance on testing behavior changes during refactoring
read-when:
  - refactoring code that changes observable behavior
  - updating tests after behavior modifications
  - PR review flags missing test coverage
---

# Testing Behavior Changes

When refactoring changes observable behavior, you MUST test the NEW behavior explicitly.

## Anti-pattern

Relying on existing tests to pass is insufficient. Existing tests verify OLD behavior - they may pass even when the new behavior is incorrect or untested.

## Example

**Scenario**: Changing "dismiss on Escape/q/Space" to "dismiss on any key"

**Wrong**: Verify existing tests for Escape/q/Space still pass. Tests pass, but new behavior (any key dismisses) is untested.

**Correct**: Add explicit test pressing an arbitrary key NOT in the original set:
```python
async def test_dismisses_on_arbitrary_key(self):
    await pilot.press("x")  # Not escape/q/space
    assert screen.is_closed
```

## Rule

When behavior changes, ask: "What does my change enable that wasn't possible before?" Write a test for that new capability.
```

---

#### 14. Post-refactoring comment hygiene

**Location:** `docs/learned/code-quality/comment-hygiene.md`
**Action:** CREATE
**Source:** [PR #8275]

**Draft Content:**

```markdown
---
description: Requirements for maintaining comment accuracy after refactoring
read-when:
  - refactoring code with existing comments
  - reviewing PRs that include refactoring
  - fixing inaccurate documentation
---

# Post-Refactoring Comment Hygiene

After ANY refactoring, review ALL comments in the affected code for accuracy.

## Why This Matters

Inaccurate comments are worse than no comments. They actively mislead future readers and cause bugs when readers trust the comment over the code.

## Specificity Requirements

Comments must precisely describe actual behavior:

**Vague (bad)**: "Dismiss the dialog"
**Specific (good)**: "Dismiss on any keypress (Escape, q, Space, or arbitrary keys)"

## Checklist

After refactoring, verify:
1. Docstrings describe current behavior, not historical behavior
2. Inline comments match the code they annotate
3. Type hints reflect actual types (not legacy types)
4. Parameter descriptions match current parameter semantics

## Example

**Before refactoring**: "Dismiss on Escape, q, or Space"
**After adding catch-all handler**: Comment says "Escape/q/Space" but code dismisses on ANY key
**Fix**: Update to "Dismiss on any keypress"
```

---

#### 15. Double-negative anti-pattern

**Location:** `docs/learned/code-quality/clarity-patterns.md`
**Action:** CREATE
**Source:** [PR #8275]

**Draft Content:**

```markdown
---
description: Code clarity patterns and anti-patterns
read-when:
  - simplifying conditional logic
  - reviewing code for clarity
  - addressing bot review comments about code simplification
---

# Code Clarity Patterns

## Double-Negative Anti-Pattern

Prefer single positive returns over multiple negative returns.

**Anti-pattern** (two negatives + positive):
```python
def _should_trigger_learn(*, is_learn_plan: bool, learn_status: str | None) -> bool:
    if is_learn_plan:
        return False
    if learn_status in {"completed_no_plan", "completed_with_plan", ...}:
        return False
    return True
```

**Preferred** (single declarative return):
```python
def _should_trigger_learn(*, is_learn_plan: bool, learn_status: str | None) -> bool:
    return not is_learn_plan and learn_status not in {
        "completed_no_plan", "completed_with_plan", ...
    }
```

The declarative form directly expresses the condition under which the function returns True, making the logic easier to understand at a glance.

## When Multiple Returns Are Acceptable

Multiple returns are fine when:
- Early returns handle error conditions with different error messages
- Guard clauses simplify complex logic by eliminating edge cases first
- The conditions being checked are conceptually different (not just parts of a compound condition)
```

---

#### 16. Batch-based PR review workflow

**Location:** `docs/learned/reviews/batch-workflow.md`
**Action:** CREATE (or UPDATE if reviews/ has existing doc)
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Structured approach to handling multi-comment PR reviews
read-when:
  - addressing PR review comments
  - planning commit structure for review responses
  - using pr-address workflow
---

# Batch-Based PR Review Workflow

When addressing multiple PR review comments, group them into logical batches for focused commits and clear audit trails.

## Workflow

1. **Classify comments**: Use `pr-feedback-classifier` to categorize (local fix, remote work, informational)
2. **Group into batches**: Related changes that can be committed together
3. **Per-batch process**:
   - Make code changes
   - Run `make fast-ci` to verify
   - Commit with clear message referencing the batch
   - Resolve threads via `erk exec resolve-review-threads`
4. **Final verification**: Re-run classifier to confirm all threads resolved

## Handling Ambiguous Comments

When review comments are informational or ambiguous (not clearly actionable), use `AskUserQuestion` to confirm desired action:

- "Act" - apply the suggested change
- "Dismiss" - leave as-is, post explanation

Don't guess intent - user confirmation prevents wasted work on misunderstood feedback.

## Example Batch Structure

- **Batch 1 (logic)**: Simplify conditional in function X
- **Batch 2 (extraction)**: Extract repeated pattern to helper
- **Batch 3 (docs)**: Fix inaccurate docstring (user decision required)
```

---

#### 17. Bot review false positive verification

**Location:** `docs/learned/pr-operations/bot-reviews.md`
**Action:** CREATE (or UPDATE if exists)
**Source:** [Impl]

**Draft Content:**

```markdown
## Bot False Positive Detection

When bots flag code for changes, verify the suggestion before applying:

1. **Read surrounding context**: The flagged code may already have the suggested fix nearby
2. **Check for LBYL patterns**: Bot might flag a line without noticing the check exists on the previous line
3. **Verify against codebase style**: Bot suggestions may not match erk's conventions (e.g., LBYL vs EAFP)

**Example false positive**: Bot suggests adding error handling to a line, but the LBYL check already exists on the line above - bot just didn't see it.

**Process**:
1. Read 5-10 lines before and after the flagged code
2. Check if the suggested improvement already exists
3. If false positive: dismiss thread with explanation
4. If legitimate: apply fix
```

---

#### 18. pr-feedback-classifier state sensitivity

**Location:** `docs/learned/pr-operations/classifier-usage.md`
**Action:** CREATE (or UPDATE if exists)
**Source:** [Impl]

**Draft Content:**

```markdown
## Classifier State Sensitivity

The `pr-feedback-classifier` output changes between runs as threads are resolved.

**Observed behavior**:
- First run: Discussion comment marked "informational"
- Resolve review threads
- Second run: Same discussion comment now marked "actionable"

**Why this happens**: The classifier considers resolution state. After resolving review threads, related discussion comments become the primary actionable items.

**Implication**: Don't cache classifier output. Re-run after making changes to get current state. This is correct behavior - explicit replies to discussion comments are still needed even after resolving the underlying issue.
```

---

#### 19. Pure function helpers in TUI

**Location:** `docs/learned/tui/architecture.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section:

```markdown
## Pure Function Helpers

Extract business logic to testable pure functions outside the App class.

**Benefits**:
- Unit testable without app context
- Reusable across multiple operations
- Easier to reason about in isolation

**Examples**:
- `_should_trigger_learn(is_learn_plan, learn_status)` - decision logic for learn triggering
- `_last_output_line(result)` - error message extraction from operation results

**Pattern**:
```python
# Module-level pure function
def _should_trigger_learn(*, is_learn_plan: bool, learn_status: str | None) -> bool:
    return not is_learn_plan and learn_status not in {...}

# Usage in App method
class ErkApp(App):
    async def _land_pr_async(self, ...):
        if _should_trigger_learn(is_learn_plan=..., learn_status=...):
            # trigger learn
```

See `src/erk/tui/app.py` for implementation examples.
```

---

#### 20. Extraction threshold guidelines

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #8275]

**Draft Content:**

Add section:

```markdown
## Extraction Threshold Guidelines

**Rule of thumb**: 3+ occurrences = extract to helper

**When to extract immediately**:
- Pattern already appears 3+ times
- Pattern is complex (multi-line, nested logic)
- Pattern has a clear name that improves readability

**When to wait**:
- Only 1-2 occurrences (may not generalize)
- Pattern is trivial (single expression)
- Extraction would require complex parameterization

**Example from PR #8275**: Error extraction pattern appeared 9 times as:
```python
next((ln for ln in reversed(result.output_lines) if ln), "Unknown error")
```

Extracted to `_last_output_line(result)` - clear name, single source of truth, testable in isolation.
```

---

### LOW Priority

#### 21. Bot activity log pattern

**Location:** `docs/learned/ci/bot-activity-logs.md`
**Action:** CREATE
**Source:** [PR #8275]

**Draft Content:**

```markdown
---
description: Pattern for bot activity logs showing violation lifecycle
read-when:
  - understanding bot comment patterns
  - debugging CI bot behavior
---

# Bot Activity Log Pattern

GitHub Apps that post automated reviews often include activity logs showing violation progression:

**Structure**:
- Detection timestamp and violation description
- Fix attempt with commit reference
- Verification result with emoji indicator

**Emoji indicators**:
- Warning/error state
- Fixed/resolved state
- Timestamps for tracking progression

This pattern helps trace the lifecycle of a violation from detection through resolution.
```

---

#### 22. pr-address output format standard

**Location:** `docs/learned/workflows/pr-address-format.md`
**Action:** CREATE
**Source:** [PR #8275]

**Draft Content:**

```markdown
---
description: Standard format for automated PR update comments
read-when:
  - implementing pr-address automation
  - debugging pr-address output
---

# PR Address Output Format

Automated PR update comments should follow this structure:

1. **Summary line**: What was addressed
2. **Bullet points**: Specific changes made
3. **Technical details**: Model used, workflow run link, commit SHAs
4. **Traceability**: Links to enable auditing

This format ensures reviewers can quickly understand what changed and trace the automation.
```

---

#### 23. Skill context:fork isolation limits

**Location:** `docs/learned/commands/skill-isolation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Limitations of skill context:fork metadata
read-when:
  - using skills that require isolation
  - debugging skill context bleeding
  - working with pr-feedback-classifier
---

# Skill context:fork Isolation Limits

**TRIPWIRE**: When invoking skills that need isolated context

The `context: fork` metadata in skill definitions only provides isolation in interactive mode. In `--print` mode (used by automation), skill context bleeds into the parent agent.

**Workaround**: Use explicit Task tool with skill file path:

```python
Task(
    subagent_type="general-purpose",
    prompt=f"Load .claude/skills/pr-feedback-classifier.md and classify..."
)
```

This creates true subagent isolation regardless of mode.

**Affected skills**: `pr-feedback-classifier` and any skill requiring isolated context for accurate classification.
```

---

## Contradiction Resolutions

No contradictions found. All existing documentation is consistent with the new implementation.

**Verified**:
- Background worker patterns match implementation
- Learn status metadata field names consistent
- Error handling patterns match Textual async docs
- Learn plan detection logic aligns across CLI and TUI

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced files exist and contain current information.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Skill context:fork isolation failure

**What happened:** Invoking `pr-feedback-classifier` via Skill tool caused classifier context to bleed into parent agent, corrupting classification results.
**Root cause:** `context: fork` metadata only works in interactive mode, not `--print` mode.
**Prevention:** Always use explicit Task tool with skill file path for skills requiring isolation.
**Recommendation:** TRIPWIRE - document in `docs/learned/commands/skill-isolation.md`

### 2. Pre-existing format violations blocking CI

**What happened:** Format check failed on test files during PR address workflow, even though the formatting issues were unrelated to the review comments being addressed.
**Root cause:** Pre-existing formatting violations in test files block CI regardless of what changes are being made.
**Prevention:** Run `make fast-ci` or `ruff format --check tests/` before starting PR address workflow.
**Recommendation:** TRIPWIRE - document in `docs/learned/pr-operations/tripwires.md`

### 3. Iterative formatting fix cascade

**What happened:** Multiple CI failures due to ruff's multi-line formatting rules - fixing one issue exposed additional issues.
**Root cause:** Ruff enforces one-argument-per-line when calls span multiple lines. Incremental edits don't account for cascading requirements.
**Prevention:** Run `ruff format --diff` after edits to catch ALL formatting issues before CI.
**Recommendation:** ADD_TO_DOC - document in `docs/learned/testing/tripwires.md`

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. TUI-CLI learn trigger synchronization

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before modifying learn trigger logic in TUI or CLI
**Warning:** Changes to `_should_trigger_learn` (TUI) require updating `_check_learn_status_and_prompt` (CLI) and vice versa. The two must stay synchronized.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents silent drift between the two learn trigger implementations. The TUI path was added after the CLI path, so future maintainers might forget to update both when changing learn trigger conditions.

### 2. Bot duplicate feedback handling

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When addressing bot review comments
**Warning:** Check if bot posted both review thread AND discussion comment about same issue. Both need explicit handling: resolve thread + reply to discussion comment.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

GitHub Apps commonly post both inline review threads and top-level summary comments. Thread resolution alone doesn't acknowledge the summary comment, leaving loose ends in PR discussions.

### 3. Pre-existing format violations blocking PR address

**Score:** 5/10 (Non-obvious +1, Cross-cutting +2, Silent failure +2)
**Trigger:** Before starting PR address workflow
**Warning:** Run `make fast-ci` or `ruff format --check` to identify pre-existing format violations that will block CI later.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

Format debt accumulates in test files especially. When addressing unrelated review comments, these pre-existing violations surface and block CI, causing confusion and wasted cycles.

### 4. Warning vs error severity for chained operations

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When implementing multi-step chained background operations in TUI
**Warning:** Primary operation success determines severity. Secondary operation failures after primary success should show as warnings, not errors.
**Target doc:** `docs/learned/tui/tripwires.md`

This pattern ensures users understand their main action succeeded even when auxiliary steps fail. Using errors for secondary failures would alarm users unnecessarily.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Ruff multi-line formatting cascade

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, External tool quirk +1)
**Notes:** Affects test files specifically. Could escalate to full tripwire if pattern repeats across more PRs. The formatting rules are subtle - most developers don't expect one-argument-per-line enforcement unless line length is exceeded.

### 2. Textual catch-all key handler testing

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to Textual TUI testing. May become HIGH priority if more modal screens are added that need catch-all key handling. The pattern of testing with keys NOT in BINDINGS is counter-intuitive but essential for verifying catch-all behavior.

### 3. Skill context:fork isolation limits

**Score:** 2/10 (Non-obvious +1, External tool quirk +1)
**Notes:** Specific to Claude Code `--print` mode edge case. Important for automation but rarely encountered in interactive use. Documented primarily for completeness and to prevent future debugging sessions.

### 4. pr-feedback-classifier state sensitivity

**Score:** 2/10 (Non-obvious +1, Repeated pattern +1)
**Notes:** Normal and correct behavior, but surprising the first time encountered. The classifier's output changing between runs is by design - it reflects the current resolution state. Documentation helps set expectations.
