# Documentation Plan: Migrate session storage to GitHub Gists and streamline TUI title display

## Context

This plan captures learnings from PR #7765, which implemented two primary changes: (1) worktree pool slot utilities for managing isolated implementation environments, and (2) TUI simplification by removing the truncated `title` column in favor of showing only `full_title`. The implementation touched 34 files with +1139/-283 lines changed.

The sessions revealed several cross-cutting patterns that warrant documentation. Most notably, the systematic removal of a frozen dataclass field (`PlanRowData.title`) cascaded through 6+ files and exposed hidden bugs in test constructors. This validates the need for a comprehensive dataclass field removal checklist. Additionally, the new slot utility module (`src/erk/cli/commands/slot/common.py`) establishes architectural patterns for worktree pool management that future work will build upon.

A critical meta-context emerged: this PR exists in a same-day revert cycle where session storage was migrated from gists to branches (PR #7757, Feb 21) and then reverted back to gists (PR #7765, same day). While the actual code changes in #7765 focus on slot utilities and TUI simplification, the session storage context explains why existing documentation references outdated branch-based storage methods. Capturing the revert rationale prevents future architectural thrashing.

## Raw Materials

PR #7765: https://github.com/schrockn/erk/pull/7765

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 20    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 6     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action before new content is added:

### 1. Session lifecycle field references

**Location:** `docs/learned/sessions/lifecycle.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `last_session_gist_url`, `last_session_gist_id` fields
**Cleanup Instructions:** These fields were removed in PR #7757 (branch-based storage) but will be re-added when gist storage is restored. Verify field names match the restored implementation and update any stale method signatures.

### 2. Session discovery method references

**Location:** `docs/learned/architecture/session-discovery.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `create_gist()` method, `last_session_gist_url`, `last_session_gist_id`
**Cleanup Instructions:** Architecture description is conceptually correct but references removed methods/fields. After gist storage is restored, update method signatures and field names to match the new implementation.

### 3. Learn pipeline workflow method signature

**Location:** `docs/learned/planning/learn-pipeline-workflow.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `_download_remote_session_for_learn()` method signature
**Cleanup Instructions:** Workflow description is valid but method references are outdated. Grep for current implementation and update the source pointer.

### 4. Plan row data title field

**Location:** `docs/learned/tui/plan-row-data.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `title` field documentation
**Cleanup Instructions:** Remove `title` field documentation (approximately line 29). Document that only `full_title` remains after PR #7765 simplification.

## Documentation Items

### HIGH Priority

#### 1. Worktree pool slot utilities

**Location:** `docs/learned/cli/worktree-pool-slots.md`
**Action:** CREATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
# Worktree Pool Slot Utilities

## Overview

The slot utility module provides functions for managing worktree pool slots. These utilities enable on-demand worktree creation and reclamation for isolated implementation environments.

See `src/erk/cli/commands/slot/common.py` for implementation.

## Core Concepts

### Slot Allocation Strategy

The `find_next_available_slot()` function implements on-demand slot creation. It only targets slots where no worktree exists on disk: not in state.assignments, not in state.slots, and no orphaned directory. This ensures creation only uses truly empty slots.

### Slot Reuse Strategy

The `find_inactive_slot()` function implements slot reclamation when the pool is full. It prefers slots in order (lowest slot number first) and skips slots with uncommitted changes to prevent data loss.

### Placeholder Branches

Slots use a placeholder branch pattern `__erk-slot-XX-br-stub__` to mark allocated but unused slots. The `is_placeholder_branch()` utility detects these branches.

## Key Functions

- `find_next_available_slot()`: Allocates the next truly empty slot
- `find_inactive_slot()`: Finds a reclaimable slot when pool is full
- `is_placeholder_branch()`: Detects placeholder branch pattern
- `SlotAllocationResult`: Dataclass capturing allocation outcome

## Tripwires

- Before creating placeholder branches for worktree slots: Use `__erk-slot-XX-br-stub__` pattern and `is_placeholder_branch()` utility. Do not create ad-hoc placeholder names.
```

---

#### 2. Frozen dataclass field removal checklist

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session e1edea12-part1, e1edea12-part2

**Draft Content:**

```markdown
## Frozen Dataclass Field Removal

**Trigger:** Before removing a field from `@dataclass(frozen=True)`

**Warning:** Search for 7 places before committing:

1. Field definition in the dataclass
2. Docstring attributes section
3. `field=` keyword arguments in constructors
4. `.field` attribute access
5. Test assertions using the field
6. Serialization logic (e.g., `dataclasses.asdict()`)
7. Filtering/search predicates

Run full test suite before committing. Manual `DataclassName()` constructors in tests are particularly brittle and may expose hidden positional dependencies.

**Root cause:** Tests using direct dataclass constructors instead of test helpers become fragile during schema evolution. Removing one field can expose missing required fields that were accidentally "filled" by positional ordering.

See session e1edea12-part2 for an example where removing `title=` exposed a missing `lifecycle_display=` field.
```

---

#### 3. Idempotent sanitize_worktree_name behavior

**Location:** `docs/learned/conventions.md` (tripwires section)
**Action:** UPDATE (add tripwire)
**Source:** [PR #7765]

**Draft Content:**

```markdown
## Idempotent Worktree Name Sanitization

**Trigger:** Before calling `sanitize_worktree_name()` on already-sanitized input

**Warning:** Function is idempotent when input has timestamp suffix. The `has_timestamp_suffix()` check prevents double-sanitization by returning input unchanged if it already ends with a valid timestamp pattern.

This prevents bugs like:

- `my-branch-02-21-1530` becoming `my-branch-02-21-1530-02-21-1531`
- Double-appending timestamps when sanitization is called multiple times in a pipeline

See `packages/erk-shared/src/erk_shared/naming.py` for implementation.
```

---

#### 4. Session storage revert rationale

**Location:** `docs/learned/architecture/session-storage-revert.md`
**Action:** CREATE
**Source:** [Impl] Session context + gap analysis

**Draft Content:**

```markdown
# Session Storage Architecture: Gist vs Branch

## Historical Context

On Feb 21 2026, session storage underwent a same-day architectural change:

1. **PR #7757**: Migrated FROM gists TO branch-based storage
2. **PR #7765** (same day): Migrated FROM branches BACK TO gists

## Why This Document Exists

This rapid reversal indicates one of:

- Incomplete testing before merge of #7757
- Missing requirements in original planning
- Changed constraints discovered post-merge

**This document captures the reasoning to prevent future thrashing.**

## Trade-offs

### Gist-based Storage (Current)

- Simpler: Single API call to store/retrieve
- No branch pollution in the repository
- Works across all repos (gists are user-scoped)

### Branch-based Storage (Reverted)

- Ties session data to repository
- Creates branch clutter
- Requires cleanup automation

## Recommendation

When considering session storage changes in the future, review this document and the PR discussions for #7757 and #7765 before proceeding.
```

---

### MEDIUM Priority

#### 5. Timestamp suffix utilities

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
## Timestamp Suffix Utilities

The `erk-shared` package provides utilities for idempotent timestamp handling in branch and worktree names:

- `has_timestamp_suffix(name)`: Checks if a name already ends with a timestamp pattern (e.g., `-02-21-1530`)
- `format_branch_timestamp_suffix()`: Creates a consistent timestamp suffix for the current time

**Usage pattern:** Always check `has_timestamp_suffix()` before appending a new timestamp to prevent double-timestamping.

See `packages/erk-shared/src/erk_shared/naming.py` for implementation.
```

---

#### 6. Objective extraction fallback logic

**Location:** `docs/learned/objectives/objective-extraction.md`
**Action:** CREATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
# Objective Extraction Fallback

## Overview

When landing a PR associated with an objective, the system needs to extract the objective number to update it. The primary source is plan metadata, but this can be lost if the PR body is overwritten during implementation.

## Fallback Strategy

The `get_objective_for_branch()` function implements a two-tier extraction:

1. **Primary:** Parse `objective_id` from plan metadata (PR body YAML block)
2. **Fallback:** Parse from branch name pattern `P123-O456-slug`

This ensures objective updates still work even when metadata is lost.

## When Fallback Activates

- PR body manually edited, removing YAML block
- Implementation process overwrote PR description
- Branch was created with objective association but PR body wasn't updated

See `src/erk/cli/commands/objective_helpers.py` for implementation.
```

---

#### 7. Comment-first UX pattern

**Location:** `docs/learned/tui/ux-patterns.md`
**Action:** CREATE
**Source:** [Impl] Session 423c6f1b

**Draft Content:**

```markdown
# Comment-First UX Pattern

## Pattern

When making visual changes to the TUI (removing columns, changing layouts), use a two-phase approach:

1. **Preview phase:** Comment out the code, don't delete
2. **Validation phase:** User confirms the change looks correct
3. **Cleanup phase:** Delete all commented code

## Rationale

This pattern allows quick rollback if the visual change is rejected. The user said "comment it out, but don't delete fetching and other plumbing" to preview, then "this is better. drop everything related to title" after validation.

## Anti-pattern

Immediately deleting code for visual changes forces recreation if the change is rejected. Use comments as a staging area for visual experiments.
```

---

#### 8. Manual constructor brittleness

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session e1edea12-part2

**Draft Content:**

```markdown
## Test Constructor Patterns

### Prefer Test Helpers Over Direct Constructors

Tests using direct dataclass constructors like `PlanRowData(id="1", title="Test", ...)` are brittle during schema evolution. When fields are added or removed, these constructors break.

**Prefer:** Test helper functions like `make_plan_row()` that abstract field management and provide sensible defaults.

**Use direct constructors only for:** Edge cases that can't be expressed via helpers (e.g., testing `plan_url=None` behavior).

### Why This Matters

In session e1edea12-part2, removing the `title` field from `PlanRowData` exposed a hidden bug: two test constructors were missing the required `lifecycle_display` field. They had worked accidentally due to positional argument ordering.
```

---

#### 9. Backward-compatible migration pattern

**Location:** `docs/learned/architecture/backward-compatible-migrations.md`
**Action:** CREATE
**Source:** [PR #7765]

**Draft Content:**

````markdown
# Backward-Compatible Migrations

## Pattern

When renaming or changing patterns that appear in persistent data (branch names, file paths, config keys), support both old and new formats during a transition period.

## Example: Branch Prefix Migration

When migrating from `plan/` to `planned/` branch prefixes:

```python
# Regex supports both old and new prefixes
pattern = r"^(plan|planned)/.*"
```
````

This allows existing branches to continue working while new branches use the updated prefix.

## When to Remove Backward Compatibility

Remove support for the old format when:

- All existing data has been migrated
- Sufficient time has passed for caches to expire
- No active PRs reference the old format

````

---

#### 10. Source pointer maintenance

**Location:** `docs/learned/documentation/source-pointer-maintenance.md`
**Action:** CREATE
**Source:** [PR #7765] PR review comment

**Draft Content:**

```markdown
# Source Pointer Maintenance

## Problem

Documentation with line number references (e.g., "See file.py:45-60") goes stale when code is refactored. The audit bot detected stale line references in existing docs.

## Best Practices

1. **Prefer symbol references over line numbers:** "See the `find_next_available_slot()` function" instead of "See slot/common.py:106-137"

2. **Use grep-able identifiers:** Include function/class names so agents can locate the current position

3. **Reserve line numbers for:** Multi-line patterns that span anonymous code blocks

4. **Consider automation:** Track source file modification times and flag docs for review when sources change

## Maintenance Pattern

When refactoring code referenced in docs:
1. Search for the file path in `docs/learned/`
2. Update any line number references
3. Verify symbol references still resolve
````

---

### LOW Priority

#### 11. TUI title column removal

**Location:** `docs/learned/tui/plan-row-data.md`
**Action:** UPDATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
## Field Changes (PR #7765)

The `title` field was removed from `PlanRowData` in favor of using only `full_title`. The truncated title display was deemed unnecessary UI complexity.

**After PR #7765:** Only `full_title` remains. There is no separate `title` field.

Update any code referencing `row.title` to use `row.full_title` instead.
```

---

#### 12. Fake factory parameter evolution

**Location:** `docs/learned/testing/fake-driven-testing.md`
**Action:** UPDATE
**Source:** [Impl] Session e1edea12-part1

**Draft Content:**

```markdown
## Factory Parameter Evolution

When removing a field from a dataclass, test factory functions need updates. If callers pass the same value positionally:

**Before:** `make_plan_row(plan_id, title)` where callers use `make_plan_row("1", "Test")`
**After:** `make_plan_row(plan_id, full_title)` - rename parameter instead of removing

This preserves positional usage patterns while updating the underlying field.
```

---

#### 13. Test table column index maintenance

**Location:** `docs/learned/testing/table-test-patterns.md`
**Action:** UPDATE
**Source:** [Impl] Session e1edea12-part1

**Draft Content:**

```markdown
## Column Index Assertions

When removing a column from a TUI DataTable, test assertions referencing column indices must be updated:

1. Search for `values[N]` patterns in test files
2. Decrement all indices after the removed column position
3. Update column count assertions
4. Update inline comments documenting column positions

**Fragility note:** Hardcoded indices are brittle. Consider using symbolic constants or helper methods to calculate indices, reducing maintenance burden during column changes.
```

---

#### 14. Plan mode scope triggers

**Location:** `docs/learned/planning/plan-mode-triggers.md`
**Action:** UPDATE
**Source:** [Impl] Session 423c6f1b

**Draft Content:**

```markdown
## Scope Decision Framework

**Enter plan mode when:**

- Multi-file refactoring (3+ files)
- Cascading changes across layers (dataclass -> provider -> UI -> tests)
- Unclear scope requiring discovery

**Execute directly when:**

- Single-file changes
- Comment/uncomment operations
- Scope is fully known upfront
```

---

#### 15. Learn command output format

**Location:** `docs/learned/commands/learn-command.md`
**Action:** UPDATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
## Output Format

The learn command output distinguishes between plan backends:

- **Draft PR backend:** "Learn plan saved as draft PR #123"
- **Issue backend:** "Learn plan saved as issue #123"

This clarity helps users understand where to find their learn plan.
```

---

#### 16. TUI title column removal validation

**Location:** `docs/learned/tui/plan-table-columns.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 423c6f1b + e1edea12

**Draft Content:**

```markdown
## Pattern Validation

The 6-step TUI column removal pattern was validated during PR #7765:

1. Column definition (`add_column`)
2. Row value extraction (`_row_to_values`)
3. Data type field
4. Data provider construction (real + fake)
5. Filtering logic
6. Test fixtures

Session e1edea12 successfully applied this pattern, confirming its completeness.
```

---

#### 17. LBYL multi-path example

**Location:** `docs/learned/architecture/lbyl-patterns.md` or dignified-python skill
**Action:** UPDATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
## Multi-Path LBYL Example

The `extract_objective_number()` function demonstrates proper 3-path LBYL error handling:

1. Check if input matches expected pattern
2. If match, extract and return value
3. If no match, return sentinel (None) or raise specific error

This avoids try/except for control flow while handling multiple failure modes cleanly.

See `src/erk/cli/commands/objective_helpers.py` for implementation.
```

---

#### 18. API boundary definition

**Location:** dignified-python skill
**Action:** UPDATE
**Source:** [PR #7765]

**Draft Content:**

```markdown
## API Boundary Definition

The LBYL rule ("no try-except for control flow") has exceptions at API boundaries. Valid API boundaries include:

- Gateway implementations wrapping external services
- CLI entry points handling user input
- File I/O operations where existence checks race with operations

**Not API boundaries:** Internal function calls, dataclass operations, dictionary access.
```

---

## SHOULD_BE_CODE Items

These items should become code artifacts (docstrings, type annotations) rather than documentation:

### 1. Slot utility docstrings

**Action:** CODE_CHANGE
**Location:** `src/erk/cli/commands/slot/common.py`
**What to add:** Comprehensive docstrings for `extract_slot_number()`, `get_placeholder_branch_name()`, and `get_pool_size()`. These are single-artifact utilities whose behavior belongs in code documentation, not docs/learned/.

### 2. Slot helper docstrings

**Action:** CODE_CHANGE
**Location:** `src/erk/cli/commands/slot/common.py`
**What to add:** Docstring for `generate_slot_name()` explaining the naming pattern. This internal helper's pattern is self-evident but warrants a brief inline explanation.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Manual dataclass constructor brittleness

**What happened:** Removing `title=` from `PlanRowData` constructors in tests exposed a missing `lifecycle_display=` field that had worked accidentally due to positional ordering.

**Root cause:** Tests used direct `PlanRowData()` constructors instead of the `make_plan_row()` helper. When fields were removed, hidden positional dependencies surfaced.

**Prevention:** Prefer test helper functions that abstract field management. Use direct constructors only for edge cases that can't be expressed via helpers.

**Recommendation:** TRIPWIRE - Add to docs/learned/testing/tripwires.md

### 2. Replace-all pattern matching hazard

**What happened:** Using `replace_all=True` to remove `title="Test"` from PlanRowData constructors also matched a function parameter named `title: str` in an unrelated function.

**Root cause:** The replacement pattern was too broad and matched more than intended.

**Prevention:** Craft patterns to include surrounding context unique to the target (e.g., multiple lines with unique field combinations), or use multiple targeted edits instead of replace-all.

**Recommendation:** ADD_TO_DOC - Include in edit tool best practices

### 3. Column index test fragility

**What happened:** Tests with `values[4]` assertions required manual updates when a column was removed.

**Root cause:** Hardcoded indices create maintenance burden during schema changes.

**Prevention:** Consider symbolic constants or helper methods to calculate column indices. Document column order in comments.

**Recommendation:** CONTEXT_ONLY - Already addressed in test patterns doc

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Frozen dataclass field removal checklist

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +1: incomplete removal causes test failures)

**Trigger:** Before removing a field from `@dataclass(frozen=True)`

**Warning:** Search for 7 places: (1) field definition, (2) docstring attributes, (3) `field=` in constructors, (4) `.field` access, (5) test assertions, (6) serialization logic, (7) filtering/search predicates. Run full test suite before committing.

**Target doc:** `docs/learned/refactoring/tripwires.md`

This is highly tripwire-worthy because: (a) the 7-place search is non-obvious and easy to miss, (b) incomplete removal causes cascading test failures that are tedious to debug, (c) the pattern applies to every frozen dataclass in the codebase, and (d) session e1edea12 demonstrated the exact failure mode (hidden positional dependencies) that this tripwire prevents.

### 2. Idempotent sanitize_worktree_name

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** Before calling `sanitize_worktree_name()` on already-sanitized input

**Warning:** Function is idempotent when input has timestamp suffix (has_timestamp_suffix() check). Returns input unchanged; no double-sanitization.

**Target doc:** `docs/learned/conventions.md` tripwires

This prevents subtle bugs where names get double-timestamped in pipelines that call sanitization multiple times.

### 3. Placeholder branch pattern

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2: affects slot allocation logic)

**Trigger:** Before creating placeholder branches for worktree slots

**Warning:** Use `__erk-slot-XX-br-stub__` pattern and `is_placeholder_branch()` utility from `src/erk/cli/commands/slot/common.py`. Do not create ad-hoc placeholder names.

**Target doc:** `docs/learned/cli/worktree-pool-slots.md` tripwires

Maintaining consistent placeholder naming is critical for the slot allocation algorithm to work correctly.

### 4. Timestamp suffix utilities

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2: applies to all branch/worktree name handling)

**Trigger:** Before appending timestamp suffixes to branch or worktree names

**Warning:** Use `has_timestamp_suffix()` to check existing suffix, `format_branch_timestamp_suffix()` to create consistent format. Prevents double-timestamping.

**Target doc:** `docs/learned/conventions.md` tripwires

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. TUI table column removal

**Score:** 3/10 (Non-obvious +2: 6-place update, Repeated pattern +1)

**Notes:** The 6-step pattern is already documented and was validated in this PR. May reach threshold if pattern is not followed consistently in future work.

### 2. Manual dataclass constructor brittleness

**Score:** 3/10 (Non-obvious +2: hidden positional dependencies, Repeated pattern +1)

**Notes:** Affects tests more than production code. May not meet cross-cutting threshold since it's primarily a testing concern rather than a production code concern.

### 3. Filter field migration

**Score:** 2/10 (Cross-cutting +2: affects filtering logic across multiple commands)

**Notes:** Specific to this refactor's field rename. May not generalize beyond this case.

### 4. Test index adjustment after column removal

**Score:** 2/10 (Cross-cutting +2: affects all table tests)

**Notes:** Specific to TUI testing. May be too narrow for a universal tripwire.

### 5. Commented code cleanup

**Score:** 2/10 (Repeated pattern +1, Non-obvious +1: agents don't always delete)

**Notes:** More of a code quality issue than a tripwire. Could be addressed with a linter rule instead.

### 6. Source pointer maintenance

**Score:** 3/10 (Non-obvious +2: line numbers drift silently, Cross-cutting +2: affects all learned docs)

**Notes:** Strong candidate but needs an automation solution before becoming a tripwire. Currently manual verification is required.
