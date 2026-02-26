# Documentation Plan: Replace fix-conflicts modal with lightweight toast pattern

## Context

PR #8276 implemented a significant architectural change in the erk TUI: replacing the synchronous streaming modal pattern for the "Fix Conflicts" action with the lightweight operations pattern (toast notification + background worker). This involved refactoring both the keybinding handler (`action_fix_conflicts_remote`) and the command palette handler (`execute_command`) to dismiss the detail screen, show an immediate toast, and delegate to an app-level async worker method.

Beyond the implementation itself, the PR triggered an extensive investigation into a seemingly unrelated issue: plan-header metadata blocks disappearing from PR bodies. Three investigation sessions traced this to a fundamental architectural weakness where `gt submit` operations outside erk's protected pipeline destroy custom PR body content. This investigation uncovered the Stage 1 vs Stage 2 PR body format inconsistency, the capture-before-modify pattern requirement, and the brittleness of separator-based extraction logic.

Documentation from this work is valuable because: (1) the operations pattern for "fire and forget" dispatch actions is now established and will be reused; (2) the metadata preservation investigation revealed cross-cutting concerns that affect all PR operations; and (3) patterns discovered for testing keybinding actions and handling automated review bots are reusable.

## Raw Materials

Session analysis files and gap analysis are available in `.erk/scratch/sessions/cc1b3e94-e147-44e2-a08d-d0f7905484e9/learn-agents/`.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 15    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. PR Body Format Specification

**Location:** `docs/learned/reference/pr-body-format-spec.md`
**Action:** CREATE
**Source:** [Impl] (sessions 431877dd-part1,2,3)

**Draft Content:**

```markdown
---
read-when: working with PR body parsing, extract_plan_header_block, assemble_pr_body, or debugging metadata loss
audit-status: new
tripwires: 2
---

# PR Body Format Specification

PR bodies in erk use two distinct formats depending on lifecycle stage.

## Stage 1: Draft Plan Format

After initial plan creation via `PlannedPrBackend.create_plan()`:

- Metadata block at TOP of body
- Structure: `metadata_block + \n + PLAN_CONTENT_SEPARATOR + details(plan_content) + footer`
- Created by `build_plan_stage_body()` and `format_plan_header_body()`

## Stage 2: Implementation Format

After `assemble_pr_body()` reassembles following submit:

- Metadata block at BOTTOM of body
- Structure: `AI_body + details(plan_content) + \n\n + metadata_block + footer`
- Extraction expects this format via `extract_plan_header_block()`

## Format Detection

Before parsing PR bodies, determine which format is present:

- Check for `PLAN_CONTENT_SEPARATOR` position relative to metadata markers
- Stage 1: separator appears after metadata block
- Stage 2: separator (if present) appears before main content

## Source References

See `src/erk/pr/shared.py` for `assemble_pr_body` and `extract_plan_header_block`.
See `src/erk/cli/pr/planned_pr.py` for `build_plan_stage_body` and `format_plan_header_body`.
```

---

#### 2. PR Body Metadata Lifecycle

**Location:** `docs/learned/pr-operations/pr-body-metadata-lifecycle.md`
**Action:** CREATE
**Source:** [Impl] (sessions 431877dd-part1,2,3)

**Draft Content:**

```markdown
---
read-when: debugging missing metadata blocks, implementing PR body updates, or calling gt submit
audit-status: new
tripwires: 3
---

# PR Body Metadata Lifecycle

Plan-header metadata blocks enable lifecycle tracking for planned PRs. Understanding when they are created, preserved, and destroyed is critical.

## Creation

Metadata blocks are created during draft PR creation:

- `PlannedPrBackend.create_plan()` calls `build_plan_stage_body()`
- Metadata rendered as HTML comment markers: `<!-- erk:metadata-block:plan-header ... -->`
- Stored in draft PR body

## Protected Operations

Erk's submit pipeline preserves metadata through capture-and-reassemble:

1. `capture_existing_pr_body` fetches current body BEFORE Graphite operations
2. `gt submit` overwrites body with commit message
3. `assemble_pr_body` extracts metadata from captured body and reinserts

Commands using this pattern: `erk pr submit`, `erk pr rewrite`

## Unprotected Operations (Destroy Metadata)

Operations that bypass the protection mechanism:

- Direct `gt submit` outside erk
- `gt restack` (may overwrite bodies)
- Any `submit_branch` call without prior capture

## Recovery

There is NO recovery mechanism for lost metadata. Once destroyed, plan-header blocks cannot be regenerated from other sources.

## Source References

See `src/erk/pr/shared.py` for the capture-before-modify pattern.
See `src/erk/cli/pr/planned_pr.py` for `PlannedPrBackend.update_metadata` requirements.
```

---

#### 3. Inline Imports for Circular Dependencies

**Location:** `docs/learned/architecture/inline-imports-circular-dependencies.md`
**Action:** CREATE
**Source:** [PR #8276] (automated review comments)

**Draft Content:**

```markdown
---
read-when: seeing automated review comments about inline imports, resolving circular import errors
audit-status: new
tripwires: 0
---

# Inline Imports for Circular Dependencies

Inline imports (imports inside functions) are typically discouraged, but they are the correct pattern when circular dependencies exist and `TYPE_CHECKING` blocks cannot be used.

## When Inline Imports Are Justified

1. **Runtime `isinstance()` usage**: When code needs to check types at runtime, imports cannot be inside `if TYPE_CHECKING` blocks
2. **Bidirectional imports between TUI modules**: Common pattern between `erk.tui.app` and screen modules

## Example: TUI Cross-Screen Delegation

The `PlanDetailScreen` imports `ErkDashApp` inside methods to avoid circular import:

```python
def action_fix_conflicts_remote(self) -> None:
    from erk.tui.app import ErkDashApp  # Inline to avoid circular import

    if isinstance(self.app, ErkDashApp):  # Runtime check requires real class
        self.app._fix_conflicts_remote_async(pr_number)
```

## When NOT to Use Inline Imports

- If the type is only needed for annotations, use `if TYPE_CHECKING` block
- If the circular dependency indicates architectural problems, refactor instead
- If the import is used in multiple methods, consider extracting a base class or interface

## Responding to Automated Reviewers

When automated reviewers flag inline imports:

- Check if `isinstance()` or other runtime type checks require the import
- Reference this doc and explain the circular dependency
- If legitimate, resolve the review thread with justification

## Source References

See `src/erk/tui/screens/plan_detail_screen.py` for the `ErkDashApp` import pattern.
```

---

### MEDIUM Priority

#### 4. Background Operations Pattern for TUI

**Location:** `docs/learned/tui/background-operations-pattern.md`
**Action:** CREATE
**Source:** [Impl] (session 6bd05fa4), [PR #8276]

**Draft Content:**

```markdown
---
read-when: implementing dispatch actions in TUI, choosing between operations pattern and streaming modal
audit-status: new
tripwires: 0
---

# Background Operations Pattern for TUI

The operations pattern provides a "fire and forget" execution model for dispatch workflows where users do not need to see live output.

## Pattern Components

1. **_start_operation(op_type)**: Registers operation, returns op_id
2. **@work(thread=True) async method**: Runs in background thread
3. **_finish_operation(op_id, result)**: Updates status bar, notifies completion

## When to Use Operations Pattern

- Dispatch workflows (address remote, fix conflicts, close plan, land PR)
- User just needs confirmation, not live output
- Operation runs on remote (GitHub Actions, etc.)

## When to Use Streaming Modal Instead

- User needs to see real-time command output
- Build, test, or other local commands with meaningful progress
- Debugging scenarios where output visibility matters

## Cross-Screen Delegation Pattern

Detail screens delegate to app-level async methods:

1. Screen dismisses itself (`self.dismiss()`)
2. Guard check with `isinstance(self.app, ErkDashApp)`
3. Call app method: `self.app._async_method(args)`

The dismiss-before-delegate order ensures the modal doesn't block UI.

## Source References

See `src/erk/tui/app.py` for `_start_operation`, `_finish_operation`, and async worker methods.
See `src/erk/tui/screens/plan_detail_screen.py` for cross-screen delegation examples.
```

---

#### 5. UI Action Test Coverage Standard

**Location:** `docs/learned/testing/ui-action-test-coverage.md`
**Action:** CREATE
**Source:** [Impl] (session 6bd05fa4), [PR #8276] (test coverage bot feedback)

**Draft Content:**

```markdown
---
read-when: adding keybinding actions to TUI screens, reviewing PR feedback about test coverage
audit-status: new
tripwires: 1
---

# UI Action Test Coverage Standard

Keybinding actions in PlanDetailScreen have two invocation paths that require separate test coverage.

## Dual Invocation Paths

1. **Keybinding path**: Direct `action_*` method call via key press
2. **Command palette path**: `execute_command()` dispatch via palette selection

These are distinct code paths even when they call the same underlying logic.

## Test Pattern for Keybinding Actions

Create a dedicated test class with two tests:

1. **Guard condition test**: Verify action does nothing when preconditions not met
2. **Happy path test**: Verify dismiss + notify + async delegation

```python
class TestPlanDetailScreenFixConflictsKeybinding:
    async def test_does_nothing_when_no_pr_number(self, app, pilot, monkeypatch):
        # Set up row without pr_number
        # Press keybinding
        # Assert nothing happened

    async def test_dismisses_notifies_and_delegates(self, app, pilot, monkeypatch):
        # Set up row with pr_number
        # Monkeypatch async method to capture call
        # Press keybinding
        # Assert screen dismissed, notify called, method invoked with correct args
```

## Monkeypatching Async Methods

Use callable wrapper to track invocation:

```python
called_with = {}
def mock_async(self_app, pr_number):
    called_with['pr_number'] = pr_number
monkeypatch.setattr(ErkDashApp, '_method_async', mock_async)
```

## Source References

See `tests/tui/test_app.py` for `TestPlanDetailScreenFixConflictsKeybinding`.
```

---

#### 6. Timeline Forensics Technique

**Location:** `docs/learned/erk-dev/timeline-forensics.md`
**Action:** CREATE
**Source:** [Impl] (session 431877dd-part3)

**Draft Content:**

```markdown
---
read-when: debugging PR body issues, reconstructing operation sequences, investigating metadata loss
audit-status: new
tripwires: 1
---

# Timeline Forensics Technique

When debugging PR operations or metadata issues, reconstruct the operation sequence using multiple data sources.

## Data Sources

1. **Git reflog**: Local operation timestamps (`git reflog --date=iso`)
2. **GitHub API events**: Force push timestamps (`gh api repos/.../issues/.../events`)
3. **CI workflow runs**: Push-triggered workflow correlation (`gh run list`)
4. **PR events**: Rename, ready-for-review, label changes

## Correlation Process

1. Identify the symptom (e.g., missing metadata block)
2. Get approximate time range from error message or PR history
3. Query each data source for that time range
4. Align events across sources using timezone conversion
5. Identify the operation that caused the issue

## Timezone Handling

- Git reflog uses LOCAL timezone (Pacific Time for most erk development)
- GitHub API uses UTC
- Convert PT to UTC: PST = UTC-8, PDT = UTC-7

Always note which timezone each timestamp uses when documenting findings.

## Multi-Worktree Considerations

Force pushes can originate from any worktree. Check:

- `git worktree list` to identify all active worktrees
- Reflog in each relevant worktree
- CI workflows may show which worktree/slot triggered them

## Source References

See session 431877dd-part3 analysis for detailed example of this technique applied to PR #8276 metadata loss investigation.
```

---

#### 7. Automated Review False Positives

**Location:** `docs/learned/review/automated-review-false-positives.md`
**Action:** CREATE
**Source:** [PR #8276] (automated review comments)

**Draft Content:**

```markdown
---
read-when: addressing automated reviewer feedback that appears incorrect, justifying dismissals
audit-status: new
tripwires: 0
---

# Handling Automated Review False Positives

Automated reviewers (bots) sometimes flag patterns that are intentional and correct. Document how to properly respond.

## Common False Positives in Erk

1. **Inline imports**: Required for circular dependencies with runtime isinstance checks
2. **Long functions**: Acceptable when extracting helpers would reduce readability
3. **Duplicate code**: Sometimes intentional for clarity in tests

## Response Protocol

1. **Verify the flag is indeed a false positive** by checking relevant docs/learned/ files
2. **Resolve the review thread** with a justification referencing the documentation
3. **Do not make code changes** just to satisfy automated reviewers when the pattern is correct

## Example Response

For inline import flags:

> This inline import is required due to circular dependency between `erk.tui.app` and `erk.tui.screens.plan_detail_screen`. The import is used for `isinstance()` runtime check, so `TYPE_CHECKING` block is not applicable. See `docs/learned/architecture/inline-imports-circular-dependencies.md`.

## When to Fix Instead

If the automated reviewer is correct:

- The flagged pattern genuinely violates standards
- A cleaner solution exists
- The documentation doesn't justify the pattern

Fix the code rather than dismissing the feedback.
```

---

#### 8. Pattern Migration: Streaming Modal to Operations

**Location:** `docs/learned/tui/pattern-migration.md`
**Action:** CREATE
**Source:** [PR #8276], [Impl] (session 6bd05fa4)

**Draft Content:**

```markdown
---
read-when: refactoring TUI actions from streaming modal to operations pattern
audit-status: new
tripwires: 0
---

# Pattern Migration: Streaming Modal to Operations

PR #8276 established the migration path from streaming modal pattern to operations pattern. Use this as a template.

## When to Migrate

- Dispatch workflows where user doesn't need live output
- "Fire and forget" actions (address remote, fix conflicts, close, land)
- Actions where immediate toast + background execution improves UX

## Migration Steps

1. **Add operations infrastructure** (if not present)
   - `_start_operation()`, `_finish_operation()` methods in ErkDashApp

2. **Create async worker method**
   - Decorator: `@work(thread=True)`
   - Parameters: `op_id: str` (if using operations tracking), action-specific args

3. **Update keybinding handler**
   - Dismiss screen first
   - Show toast via `self.notify()`
   - Guard with `isinstance(self.app, ErkDashApp)`
   - Delegate to app-level async method

4. **Update command palette handler**
   - Same pattern as keybinding handler
   - Both paths must use identical delegation logic

5. **Update tests**
   - Create dedicated keybinding test class
   - Test guard condition (no-op case)
   - Test happy path (dismiss + notify + delegate)
   - Monkeypatch async method to verify invocation

## Common Pitfalls

- **Signature mismatch**: Ensure handler calls method with correct parameters
- **Missing op_id**: If using operations tracking, generate ID before calling async method
- **Forgot dismiss**: Detail screen must dismiss before delegating to avoid z-layer blocking

## Source References

See `src/erk/tui/screens/plan_detail_screen.py` for `action_fix_conflicts_remote` migration example.
See `tests/tui/test_app.py` for `TestPlanDetailScreenFixConflictsKeybinding` test pattern.
```

---

### LOW Priority

#### 9. Update Dual-Handler Pattern Doc

**Location:** `docs/learned/tui/dual-handler-pattern.md`
**Action:** UPDATE
**Source:** [PR #8276]

**Draft Content:**

Add section on cross-screen delegation:

```markdown
## Cross-Screen Delegation

When detail screens need to invoke app-level async methods:

1. Import app class inside method (avoid circular import)
2. Guard with `isinstance(self.app, ErkDashApp)`
3. Dismiss screen BEFORE calling app method
4. Call app method with required arguments

Why dismiss first: The detail screen creates a modal layer that blocks UI updates. Dismissing ensures the main view is visible when the toast appears.

See `src/erk/tui/screens/plan_detail_screen.py` for examples.
```

---

#### 10. Update Command Execution Decision Guide

**Location:** `docs/learned/tui/command-execution.md`
**Action:** UPDATE
**Source:** [PR #8276]

**Draft Content:**

Add section on pattern selection:

```markdown
## Pattern Selection: Operations vs Streaming Modal

### Use Operations Pattern When

- Action dispatches to remote (GitHub Actions, CI, etc.)
- User just needs confirmation of dispatch
- Output is available elsewhere (GitHub UI, workflow logs)
- Examples: address_remote, fix_conflicts, close_plan, land_pr

### Use Streaming Modal When

- User needs real-time command output
- Local command execution with meaningful progress
- Debugging or investigation scenarios
- Examples: build, test, rebase (if showing progress)

### Consistency Principle

All dispatch actions should use the same pattern. If one uses operations pattern, others should too for consistent UX.
```

---

#### 11. Update Subprocess Testing Doc

**Location:** `docs/learned/testing/tui-subprocess-testing.md`
**Action:** UPDATE
**Source:** [Impl] (session 6bd05fa4)

**Draft Content:**

Add section on guard condition testing:

```markdown
## Testing Guard Conditions

Actions with preconditions (e.g., PR number required) need guard condition tests:

```python
async def test_action_does_nothing_when_precondition_not_met(self, app, pilot, monkeypatch):
    # Set up state WITHOUT required precondition
    # Press keybinding
    # Assert:
    #   - Screen NOT dismissed
    #   - Async method NOT called
    #   - No side effects occurred
```

This validates the early return / no-op path.

## Monkeypatching Async Methods

To verify async method was called with correct arguments:

```python
called = {'invoked': False, 'args': None}

def mock_method(self, *args):
    called['invoked'] = True
    called['args'] = args

monkeypatch.setattr(ErkDashApp, '_async_method', mock_method)

# ... trigger action ...

assert called['invoked']
assert called['args'] == expected_args
```
```

---

## Contradiction Resolutions

### 1. PR Body Format Mismatch (Stage 1 vs Stage 2)

**Existing doc:** Not explicitly documented (scattered across code)
**Conflict:** Two different mental models exist:
- `extract_plan_header_block` expects metadata at top (Stage 1 format)
- `assemble_pr_body` produces metadata at bottom (Stage 2 format)

**Resolution:** Create formal specification document (Item #1 above) that:
1. Defines both formats explicitly
2. Documents when format transition occurs
3. Explains how extraction logic should handle both

The extraction function currently uses `.find(PLAN_CONTENT_SEPARATOR)` which returns the FIRST occurrence. If the separator appears in AI-generated content before the expected location, extraction returns wrong boundaries. The format spec should recommend using metadata block markers as primary boundary detection.

---

## Stale Documentation Cleanup

No stale documentation detected. The existing docs check confirmed that `docs/learned/tui/` documentation is comprehensive and accurate with no phantom references.

---

## Prevention Insights

### 1. Silent Metadata Block Loss via gt submit

**What happened:** Plan-header metadata blocks disappeared from PR #8276 body after an unprotected `gt submit` operation overwrote the body with commit message content.

**Root cause:** The `gt submit` command replaces PR body with commit message. Erk's submit pipeline has a capture-before-modify pattern to preserve metadata, but direct `gt` commands bypass this protection.

**Prevention:** Always use `erk pr submit` or `erk pr rewrite` instead of direct `gt submit` for PRs with tracked metadata. Consider adding a tripwire warning for this pattern.

**Recommendation:** TRIPWIRE

### 2. Separator Pattern Collision in Extraction

**What happened:** `extract_plan_header_block` uses `.find()` to locate `\n\n---\n\n` separator, which returns the FIRST occurrence. If AI-generated content contains this pattern, extraction returns wrong boundaries.

**Root cause:** Simple string search without validation that the found separator is in the expected position relative to metadata markers.

**Prevention:** Use metadata block markers (`<!-- erk:metadata-block:plan-header -->`) as primary boundary detection instead of relying on separator pattern.

**Recommendation:** TRIPWIRE

### 3. Test Coverage Bot Duplicate Comments

**What happened:** Test coverage bot created both a review thread (PRRT_* ID) AND a discussion comment (integer ID) with identical content. Only resolving the review thread left the discussion comment unaddressed.

**Root cause:** Bot behavior creates redundant entries that require separate resolution commands.

**Prevention:** When addressing test-coverage bot feedback, always check for and address both the review thread AND discussion comment.

**Recommendation:** TRIPWIRE

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. gt submit PR Body Metadata Destruction

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before calling `gt submit` or `submit_branch` on branches with tracked PRs
**Warning:** `gt submit` overwrites PR body with commit message, destroying plan-header metadata blocks. Always use `erk pr submit` or capture body before calling Graphite operations.
**Target doc:** `docs/learned/planning/tripwires.md`

This is the highest priority tripwire because metadata loss is permanent with no recovery mechanism. Three investigation sessions traced metadata loss to this root cause. The pattern is non-obvious because developers expect PR body updates to be additive, not destructive.

### 2. Metadata Block Extraction Brittleness

**Score:** 6/10 (Non-obvious +2, Silent failure +2, Cross-cutting +2)
**Trigger:** When implementing PR body parsing logic
**Warning:** `extract_plan_header_block` searches for `\n\n---\n\n` using `.find()`, which returns FIRST occurrence. If this pattern appears in AI-generated content or plan markdown, extraction returns wrong boundaries. Use metadata block markers as primary boundary detection.
**Target doc:** `docs/learned/planning/tripwires.md`

The silent failure aspect makes this dangerous - extraction returns wrong content without raising an error, causing downstream issues that are hard to trace back to the source.

### 3. Test Coverage Bot Duplicate Comments

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** When addressing test-coverage bot review feedback
**Warning:** Test-coverage bot creates BOTH a review thread (PRRT_* ID) and a discussion comment (integer ID) with identical content. Both need resolution: use `erk exec resolve-review-threads` for threads and `erk exec reply-to-discussion-comment` for discussions.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

While lower severity than the metadata issues, this affects every PR that receives test coverage feedback and causes confusion when threads appear unresolved.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Timezone Coordination in Forensics

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Only affects debugging/investigation workflows, not production code paths. Documenting in the timeline forensics guide (Item #6) is sufficient. Would promote to tripwire if timezone confusion caused a production bug.

### 2. PR Body Format Mismatch

**Score:** 3/10 (Non-obvious +2, Silent failure +1)
**Notes:** This is more of a code quality issue that should be fixed by refactoring rather than worked around with tripwires. The format spec document will guide toward fixing the inconsistency. Would promote if refactoring is deprioritized indefinitely.
