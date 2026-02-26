# Documentation Plan: Fix: plan-header metadata block lost silently in CI update flow

## Context

This plan implements documentation learnings from PR #8331, which fixed a silent corruption bug in `ci_update_pr_body.py`. The bug caused planned-PR bodies to lose their plan-header metadata block when CI ran updates, producing corrupted output with no error or warning. The root cause was a lenient code pattern that silently proceeded with empty strings when required metadata was missing.

The fix demonstrates erk's fail-loud philosophy: explicit error handling that returns descriptive `UpdateError` variants instead of silently corrupting data. A secondary improvement raised logging levels for metadata parse failures from debug to warning, ensuring visibility in CI logs. The implementation sessions revealed a related issue: plan-implementation mismatch, where `.impl/plan.md` can become stale and contain content from a different plan entirely.

Documentation matters because these patterns represent silent failure modes that waste implementation time and produce corrupted data. Future agents need clear guidance on: (1) always failing loudly when required metadata is missing, (2) logging parse failures at warning level for CI visibility, and (3) verifying plan content matches PR title before implementation.

## Raw Materials

PR #8331

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 12 |
| Contradictions to resolve | 1 |
| Stale docs to clean up | 5 |
| Tripwire candidates (score >= 4) | 4 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These MUST be fixed FIRST before creating new documentation.

### 1. docs/learned/planning/planned-pr-lifecycle.md

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()` (function was removed - see CHANGELOG.md line 238)
**Cleanup Instructions:** Replace all references to `extract_metadata_prefix()` with the actual current pattern: `find_metadata_block()` to locate metadata and `render_metadata_block()` to serialize. The function was refactored during earlier metadata system improvements.

### 2. docs/learned/architecture/pr-body-assembly.md

**Location:** `docs/learned/architecture/pr-body-assembly.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()`
**Cleanup Instructions:** Same as above - replace references to the removed function with `find_metadata_block()` + `render_metadata_block()` pattern.

### 3. docs/learned/planning/tripwires.md

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()`
**Cleanup Instructions:** Update any tripwire text referencing the removed function to reference the current implementation pattern.

### 4. docs/learned/architecture/tripwires.md

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()`
**Cleanup Instructions:** Same - update to current function names.

### 5. docs/learned/pr-operations/draft-pr-handling.md

**Location:** `docs/learned/pr-operations/draft-pr-handling.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()`
**Cleanup Instructions:** Replace phantom function reference with current pattern.

## Contradiction Resolutions

### 1. PR Body Metadata Ordering

**Status:** RESOLVED_IN_CODE (contradiction was the bug being fixed)

**Existing doc:** `docs/learned/planning/planned-pr-lifecycle.md` documents that metadata blocks appear FIRST in PR body.

**Conflict:** The bug in `ci_update_pr_body.py` assembled the body with metadata LAST, violating the documented correct behavior.

**Resolution:** No documentation change needed. PR #8331 fixed the code to match the documented behavior by adding an early return guard when plan-header is None. The documentation was correct; the code drifted.

## Documentation Items

### HIGH Priority

#### 1. Plan-implementation mismatch tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session c9b9d009-part1

**Draft Content:**

```markdown
## Plan-Implementation Mismatch Detection

- action: "reading .impl/plan.md in plan-implement workflow"
  warning: "Verify plan content matches PR title via `gh pr view --json title`. If mismatched, the .impl/plan.md is stale - fetch actual plan from PR body with `gh pr view --json body`."
```

This tripwire addresses a silent failure mode discovered during implementation: the `.impl/plan.md` file appeared authoritative but contained content from a completely different plan. The agent only discovered this after attempting to implement nodes that were already completed in prior PRs. Without this tripwire, agents waste entire sessions implementing the wrong work.

#### 2. Required metadata validation tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8331] + [Impl]

**Draft Content:**

```markdown
## Required Metadata Block Validation

- action: "when a metadata block is required for an operation (e.g., plan-header for planned PRs)"
  warning: "Return error if find_metadata_block() returns None instead of silently proceeding with empty string. The pattern `field if field else ''` hides corruption."
```

This is the core lesson from the bug being fixed. The lenient pattern `render_metadata_block(plan_header) if plan_header is not None else ""` allowed corrupted PR bodies to be written with no error, no warning, and no visibility.

#### 3. Metadata parse failures logging tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8331] + [Impl] Session c9b9d009-part2

**Draft Content:**

```markdown
## Metadata Parse Failure Logging

- action: "logging YAML/JSON/metadata parse failures"
  warning: "Use logger.warning() not logger.debug() to ensure visibility in CI logs. Debug-level logging hides critical data corruption issues."
```

This tripwire applies to all gateway parsing (GitHub metadata, Git output, etc.). The fix changed `logger.debug()` to `logger.warning()` in `parse_metadata_blocks` to ensure parse failures appear in normal CI output.

#### 4. Stale plan detection tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Plan] Session aeb525c1

**Draft Content:**

```markdown
## Stale Plan Detection Before Implementation

- action: "implementing a plan from a previous session"
  warning: "Re-verify plan is still relevant by checking bug conditions still exist. Launch Explore agents to verify each condition mentioned in the plan."
```

Session aeb525c1 demonstrated the verification workflow: launching parallel Explore agents to check each bug condition before proceeding with implementation.

### MEDIUM Priority

#### 5. Plan verification workflow pattern

**Location:** `docs/learned/planning/plan-verification-workflow.md`
**Action:** CREATE
**Source:** [Plan] Session aeb525c1

**Draft Content:**

```markdown
---
title: Plan Verification Workflow
read_when:
  - verifying a plan is still relevant against current codebase
  - user asks to "confirm plan still relevant"
  - implementing a plan created in a previous session
---

# Plan Verification Workflow

When implementing or saving a plan, verify it's still relevant before proceeding.

## Pattern

1. User provides fully-formed plan with instruction "confirm plan still relevant"
2. Agent launches parallel Explore subagents to verify each bug/condition
3. Each subagent reports: bug still exists / already fixed / test exists or missing
4. Agent synthesizes findings and confirms plan applicability

## When to Use

- Before saving a plan that describes bugs or missing features
- Before implementing a plan created in a previous session
- When code may have changed since plan creation

## Implementation

<!-- Source: Session aeb525c1-d839-4b98-87de-3d61080c33ca (planning session) -->

Launch multiple Task/Explore agents simultaneously to verify independent conditions. Each agent reports its findings, then the parent synthesizes to determine if the plan is still valid.

See session aeb525c1 for a complete example of this workflow verifying three bugs in parallel before plan-save.
```

#### 6. Branch slug conventions

**Location:** `docs/learned/planning/branch-slug-conventions.md`
**Action:** CREATE
**Source:** [Plan] Session aeb525c1

**Draft Content:**

```markdown
---
title: Branch Slug Conventions
read_when:
  - generating a branch name from a plan title
  - naming a branch for plan-save workflow
---

# Branch Slug Conventions

Branch slugs are generated from plan titles for the plan-save workflow.

## Rules

- 2-4 hyphenated lowercase words
- Maximum 30 characters
- Capture the distinctive essence of the plan
- Drop filler words: the, a, for, implementation, plan
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate

## Examples

| Plan Title | Branch Slug |
|------------|-------------|
| "Fix: plan-header metadata block lost silently in CI update flow" | `fix-planheader-silent-loss` |
| "Add dark mode toggle to settings" | `add-darkmode-settings` |
| "Refactor gateway ABC to support async" | `refactor-gateway-async` |

## Source

<!-- Source: .claude/skills/erk-planning/plan-save.md -->

Branch slug rules are defined in the plan-save skill. The slug appears in branch names like `plnd/fix-planheader-silent-loss-02-26-1055`.
```

#### 7. CI update PR body error cases

**Location:** `docs/learned/planning/ci-update-pr-body-errors.md`
**Action:** CREATE
**Source:** [PR #8331]

**Draft Content:**

```markdown
---
title: CI Update PR Body Error Cases
read_when:
  - debugging ci_update_pr_body failures
  - adding new error cases to UpdateError
  - understanding planned-PR CI workflow
---

# CI Update PR Body Error Cases

The `ci_update_pr_body.py` script uses a discriminated union `UpdateError` for error handling.

## Error Variants

<!-- Source: src/erk/cli/commands/exec/scripts/ci_update_pr_body.py, UpdateError class -->

| Error | When It Fires | Recovery |
|-------|---------------|----------|
| `pr-not-found` | PR doesn't exist or can't be fetched | Verify PR number and permissions |
| `empty-diff` | No code changes in PR | Ensure PR has actual file changes |
| `claude-execution-failed` | Claude generation failed | Check Claude API status, retry |
| `plan-header-not-found` | Planned-PR mode but plan-header metadata missing | Investigate why metadata was lost; may need manual `gh pr edit` |

## The plan-header-not-found Case

Added in PR #8331. This error fires when:
1. The `--planned-pr` flag is set
2. `find_metadata_block(pr_body, "plan-header")` returns None

The error message includes the PR body prefix for diagnosis.

See `ci_update_pr_body.py` for the complete `UpdateError` type definition.
```

#### 8. Early return guard pattern example

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl] Session c9b9d009-part2

**Draft Content:**

Add a new section:

```markdown
## Early Return Guard Pattern

When a required field can be None, add an early return immediately after checking:

**Pattern:**
1. Call `find_metadata_block()` or similar
2. Immediately check `if result is None: return Error(...)`
3. Type narrowing now guarantees result is not None
4. Remove any dead ternary checks like `result if result is not None else fallback`

**Effect:** The early return eliminates the need for ternary fallbacks. After the guard, the type checker knows the value is not None, so any `x if x is not None else ""` becomes dead code.

<!-- Source: src/erk/cli/commands/exec/scripts/ci_update_pr_body.py -->

See `ci_update_pr_body.py` for an example where adding `if plan_header is None: return UpdateError(...)` allowed removing the dead ternary that followed.
```

#### 9. Exit plan mode hook orchestration

**Location:** `docs/learned/hooks/exit-plan-mode.md`
**Action:** CREATE (if not exists) or UPDATE
**Source:** [Plan] Session aeb525c1

**Draft Content:**

```markdown
---
title: Exit Plan Mode Hook
read_when:
  - understanding how plan mode exit is handled
  - modifying the plan-save workflow
  - debugging unexpected plan mode behavior
---

# Exit Plan Mode Hook

The exit-plan-mode hook demonstrates a hook-as-router pattern for workflow orchestration.

## Workflow

1. Agent calls `ExitPlanMode` tool
2. PreToolUse hook intercepts the call
3. Hook instructs agent to Read and display plan content
4. Hook uses `AskUserQuestion` to prompt user with options:
   - Create a plan PR (Recommended)
   - Implement here
   - Edit plan
5. Based on user selection, hook routes to appropriate skill (e.g., `erk:plan-save`)

## Key Insight

This pattern enables declarative workflow management without hardcoding state machines. The hook intercepts the tool call, gathers context, prompts the user, and routes to the appropriate next step - all through system prompts rather than code.

<!-- Source: .claude/hooks/exit-plan-mode-hook.py -->

See the exit-plan-mode-hook implementation for the complete PreToolUse pattern.
```

#### 10. setup-impl non-fatal error handling

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session c9b9d009-part1

**Draft Content:**

```markdown
## setup-impl .erk/impl-context/ Errors

- action: "setup-impl fails with 'No such file or directory' for .erk/impl-context/"
  warning: "This error is NON-FATAL on branches created before .erk/impl-context/ consolidation. Verify success with `erk exec impl-init --json` - if it returns `valid: true`, the .impl/ folder setup succeeded despite the cleanup error."
```

This documents an expected transient error during the consolidation migration period.

### LOW Priority

#### 11. Logging levels in CI

**Location:** `docs/learned/architecture/logging-levels-ci.md`
**Action:** CREATE
**Source:** [Impl] Session c9b9d009-part2

**Draft Content:**

```markdown
---
title: Logging Levels in CI
read_when:
  - choosing between debug and warning log levels
  - investigating missing log output in CI
  - adding logging to gateway parsing code
---

# Logging Levels in CI

Debug-level logging is invisible in normal CI runs, which can hide critical issues.

## Decision Framework

| Log Level | Use When | CI Visibility |
|-----------|----------|---------------|
| `debug` | Verbose tracing for local development | Hidden |
| `info` | Normal operation milestones | Visible |
| `warning` | Unexpected but recoverable situations | Visible, highlighted |
| `error` | Failures requiring attention | Visible, prominent |

## Parse Failure Pattern

Parse failures (YAML, JSON, metadata) should use `logger.warning()`, not `logger.debug()`:

- Parse failures indicate data corruption or format violations
- They need visibility without requiring debug mode
- CI logs should show these without special configuration

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, parse_metadata_blocks -->

See `parse_metadata_blocks` in metadata/core.py for an example where the log level was changed from debug to warning to improve CI visibility.
```

#### 12. Dead code elimination after type narrowing

**Location:** `docs/learned/refactoring/dead-code-elimination.md`
**Action:** CREATE or UPDATE
**Source:** [Impl] Session c9b9d009-part2

**Draft Content:**

```markdown
---
title: Dead Code Elimination After Type Narrowing
read_when:
  - adding early return guards for None checks
  - refactoring code with type narrowing
---

# Dead Code Elimination After Type Narrowing

After adding an early return guard, subsequent ternary checks become dead code.

## Pattern

**Before:**
```python
result = find_something()
# No guard - result might be None
output = format(result) if result is not None else ""
```

**After adding early return:**
```python
result = find_something()
if result is None:
    return Error("...")
# Type narrowing: result is guaranteed not None here
output = format(result)  # Ternary removed - it was dead code
```

## Why This Matters

The `result if result is not None else ""` pattern silently handles None as an empty string. This is the pattern that caused the plan-header corruption bug. After adding the early return guard, the ternary is both unnecessary (dead code) and misleading (suggests None is still possible).
```

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent Metadata Loss

**What happened:** `ci_update_pr_body.py` wrote PR bodies without plan-header metadata block, corrupting downstream systems.

**Root cause:** Two factors combined: (1) `logger.debug()` for parse failures meant no visibility in CI, and (2) lenient code pattern `field if field else ""` silently proceeded with empty string.

**Prevention:** Use `logger.warning()` for parse failures. Return explicit errors when required fields are None.

**Recommendation:** TRIPWIRE (added above as items 2 and 3)

### 2. Plan-Implementation Mismatch

**What happened:** Agent attempted to implement from `.impl/plan.md` which contained stale content from a completely different plan (Nodes 1.6/1.7/1.8 about .impl/ consolidation instead of the plan-header fix).

**Root cause:** The `.impl/` folder retained old content when the plan was regenerated on GitHub. The plan-implement workflow trusted `.impl/plan.md` as the source of truth.

**Prevention:** Cross-check `.impl/plan.md` title against `gh pr view --json title` before implementing. If they don't match, fetch actual plan from PR body.

**Recommendation:** TRIPWIRE (added above as item 1)

### 3. setup-impl False Failure

**What happened:** `setup-impl` reported exit code 1 for `git add -f .erk/impl-context/` with "No such file or directory".

**Root cause:** The cleanup step assumed `.erk/impl-context/` existed, but this branch predated the consolidation.

**Prevention:** Check `.erk/impl-context/` existence before attempting cleanup. Validate success with `erk exec impl-init --json` which correctly reports `valid: true` even when cleanup fails.

**Recommendation:** ADD_TO_DOC (item 10 above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Plan-implementation mismatch detection

**Score:** 8/10 (Non-obvious +2, Silent failure +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +1)
**Trigger:** After reading .impl/plan.md in plan-implement workflow
**Warning:** "Verify plan content matches PR title via `gh pr view --json title`. If mismatched, fetch actual plan from PR body."
**Target doc:** `docs/learned/planning/tripwires.md`

This is the highest-value tripwire. The agent in session c9b9d009-part1 discovered the mismatch only after attempting to implement nodes that were already complete. Without this check, an entire implementation session can be wasted on the wrong work. The `.impl/plan.md` file looks authoritative - nothing about it suggests staleness.

### 2. Required metadata validation

**Score:** 6/10 (Non-obvious +2, Silent failure +2, Destructive potential +2)
**Trigger:** When a metadata block is required for an operation
**Warning:** "Return error if find_metadata_block() returns None instead of silently proceeding with empty string"
**Target doc:** `docs/learned/planning/tripwires.md`

The lenient `field if field else ""` pattern was the direct cause of the corruption bug. It appears safe (graceful degradation!) but actually hides critical failures. This pattern appears throughout the codebase wherever optional metadata is handled.

### 3. Metadata parse failures logging level

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When logging YAML/JSON/metadata parse failures
**Warning:** "Use logger.warning() not logger.debug() to ensure visibility in CI logs"
**Target doc:** `docs/learned/architecture/tripwires.md`

Debug vs warning is a subtle distinction that most developers won't consider. The natural instinct is "parse failures are internal details, use debug". But in production/CI context, parse failures indicate data corruption that needs visibility. This applies to all gateway parsing across the codebase.

### 4. Stale plan detection before implementation

**Score:** 5/10 (Non-obvious +2, Repeated pattern +1, Destructive potential +2)
**Trigger:** Before implementing a plan from a previous session
**Warning:** "Re-verify plan is still relevant by checking bug conditions still exist"
**Target doc:** `docs/learned/planning/tripwires.md`

Session aeb525c1 demonstrated the correct workflow: launching parallel Explore agents to verify each bug condition before proceeding. Plans can be invalidated by other PRs landing between creation and implementation.

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. setup-impl .erk/impl-context/ cleanup failure

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** May not meet threshold because the error is visible (not silent). The cleanup failure appears in output - the issue is knowing it's non-fatal. Better suited as documentation in planning/ than as a tripwire. Included as documentation item 10 above.

### 2. Discriminated union error cases need regression tests

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Already well-covered in testing docs. Every error variant needing a test is good practice but not tripwire-worthy - it's standard test discipline. The existing fake-driven testing patterns already guide this.

## Implementation Order

For the documentation-writer agent, implement in this order:

1. **FIRST: Fix phantom references** (5 files) - Prevents false alarms when agents search for `extract_metadata_prefix()`
2. **SECOND: Add HIGH-priority tripwires** (4 items) - Prevents future silent failures
3. **THIRD: Create new docs** (5 items) - Captures new patterns
4. **FOURTH: Update existing docs** (3 items) - Enriches existing material
