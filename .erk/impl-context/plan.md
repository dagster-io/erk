# Documentation Plan: Rename "prepare" properties to "checkout" in next_steps

## Context

This plan captures documentation learnings from PR #7986, which implemented a systematic rename of internal property names from "prepare" terminology to "checkout" terminology in the `IssueNextSteps` and `DraftPRNextSteps` dataclasses. The rename aligns internal API names with user-facing command labels, following PR review feedback from #7981 that "python artifacts should align with user-facing messaging."

The implementation was a clean refactoring that touched 4 files: one source file, two test files, and one documentation file. The session revealed a non-obvious testing constraint for the erk-shared package: tests in `packages/erk-shared/tests/` must be run from within the `packages/erk-shared/` directory, not from the project root. This caused a ModuleNotFoundError during implementation that required understanding pytest import resolution to diagnose.

Future agents benefit from knowing: (1) the pytest working directory requirement for package-specific tests (prevents debugging mysterious import errors), (2) the principle of aligning internal property names with user-facing command labels (guides future API naming decisions), and (3) the pattern for testing format function output strings (ensures user-facing improvements survive refactoring).

## Raw Materials

PR #7986

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Package-specific pytest working directory

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] (session-46f50821)

**Draft Content:**

```markdown
## Package Test Working Directory

- action: "running pytest on packages/erk-shared/tests/ files from root directory"
  warning: "Must run pytest from packages/erk-shared/ directory OR use separate test commands with proper working directory context. Running from root causes ModuleNotFoundError due to incorrect import resolution for package tests."
  prevention: |
    # From root directory - WRONG
    pytest packages/erk-shared/tests/unit/output/test_next_steps.py  # Will fail

    # From package directory - CORRECT
    cd packages/erk-shared/
    pytest tests/unit/output/test_next_steps.py

    # OR run tests separately
    (cd packages/erk-shared && pytest tests/) && pytest tests/
  source: "PR #7986 session analysis"
  severity: "MEDIUM"

This tripwire applies to all test runs in the packages/erk-shared/tests/ directory. The error is non-obvious because ModuleNotFoundError doesn't indicate that changing the working directory is the solution. Developers may attempt to add __init__.py files or modify imports instead of addressing the root cause.
```

---

#### 2. Update next-steps-output.md property tables

**Location:** `docs/learned/planning/next-steps-output.md`
**Action:** UPDATE
**Source:** [PR #7986]

**Draft Content:**

```markdown
## Property Updates for IssueNextSteps

Update the property table to reflect new names:

| Property | Description |
|----------|-------------|
| `checkout` | `erk br co --for-plan {plan_number}` |
| `checkout_and_implement` | Combined checkout and implement command |
| `checkout_new_slot` | `erk br co --for-plan {plan_number} --new-slot` |
| `checkout_new_slot_and_implement` | Combined new-slot checkout and implement |

## Property Updates for DraftPRNextSteps

Update the property table to reflect new names:

| Property | Description |
|----------|-------------|
| `checkout_branch_and_implement` | Uses branch_name directly (renamed from checkout_and_implement) |
| `checkout` | `erk br co --for-pr {pr_number}` |
| `checkout_and_implement` | Uses plan number with --for-plan (renamed from prepare_and_implement) |
| `checkout_new_slot` | `erk br co --for-pr {pr_number} --new-slot` |
| `checkout_new_slot_and_implement` | Combined new-slot checkout and implement |

## Constant Update

Update constant reference: `PREPARE_SLASH_COMMAND` -> `CHECKOUT_SLASH_COMMAND`

## Naming Rationale

Properties use "checkout" terminology to align with the user-facing command labels:
- Format functions display "Checkout:" in CLI output
- The underlying command is `erk br co` (checkout)
- Internal property names now match external terminology for consistency

This follows the convention established in PR #7986 and aligns with the principle that internal APIs should use the same terminology as user-facing interfaces (see docs/learned/conventions.md).
```

---

### MEDIUM Priority

#### 3. Naming convention: internal/external alignment

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #7986]

**Draft Content:**

```markdown
## API Naming: Internal/External Alignment

**Principle:** Internal property names, function parameters, and API identifiers should align with user-facing command labels and terminology.

**Rationale:**
- Reduces cognitive load when reading code that generates user-facing output
- Makes code self-documenting by matching terminology users see
- Prevents confusion about what a property represents

**Example: Next-Steps Properties**

In PR #7986, properties in `IssueNextSteps` and `DraftPRNextSteps` were renamed from "prepare" to "checkout" because the format functions display "Checkout:" in CLI output and the underlying command is `erk br co` (checkout).

**Pattern:** When format functions display label X but properties are named Y, rename properties to X.

**Related:** See docs/learned/planning/next-steps-output.md for the complete next-steps API.
```

---

#### 4. Format function output testing pattern

**Location:** `docs/learned/testing/format-function-testing.md`
**Action:** CREATE
**Source:** [PR #7986]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for format functions
  - adding new format functions that generate user-facing output
  - modifying existing format functions
category: testing
---

# Format Function Output Testing

## When to Test Format Function Output

Format functions that generate user-facing output (CLI text, markdown, etc.) should have tests that verify:
1. Specific expected strings appear in the output
2. User-facing improvements remain after refactoring

## Pattern

When adding or modifying user-facing output in format functions, add tests that verify specific output strings appear. This ensures user-facing improvements survive refactoring.

**Example from next-steps-output:**

When the "Implement:" line was added to next-steps format functions, tests were added to verify the string appears. See `packages/erk-shared/tests/unit/output/test_next_steps.py` for the test pattern (grep for `test_format_.*_contains_implement`).

## Why This Matters

1. **Refactoring safety:** Format functions are often refactored. Output verification tests catch accidental removal of user-facing features.
2. **Documentation as code:** Tests document what output strings are considered essential.
3. **User-facing guarantees:** Tests ensure users see expected labels and instructions.

## When to Skip

Skip output verification tests for:
- Internal format functions not exposed to users
- Functions that compose other tested format functions
- Output that's covered by integration tests

## Related

- PR #7986: Added "Implement:" line to next-steps output with verification tests
- docs/learned/planning/next-steps-output.md: Next-steps format function examples
```

---

## Contradiction Resolutions

**No contradictions detected.**

The existing documentation accurately describes the current state of the code. The rename from "prepare" to "checkout" does not contradict any existing guidance - it's a naming improvement that makes the property names more consistent with the underlying `erk br co` command they generate.

## Stale Documentation Cleanup

**No stale documentation detected.**

All documentation references are current. The existing-docs-checker verified that all referenced paths in planning documentation are valid.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. ModuleNotFoundError when testing erk-shared

**What happened:** Running `pytest packages/erk-shared/tests/unit/output/test_next_steps.py` from the project root directory caused `ModuleNotFoundError: No module named 'tests.unit.output'`.

**Root cause:** Pytest import resolution works differently for packages in subdirectories. When running from root, pytest cannot resolve imports correctly for the erk-shared package tests because the package structure expects tests to be run from within the package directory.

**Prevention:** Always run package-specific tests from their package directory, not from project root. Either `cd packages/erk-shared && pytest tests/` or run tests separately with proper working directory context.

**Recommendation:** TRIPWIRE - This error is non-obvious (the error message doesn't indicate the solution), cross-cutting (affects all package tests), and causes silent failures (developers may try wrong fixes).

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Package-specific pytest working directory for erk-shared

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before running pytest on packages/erk-shared/tests/ files from root directory

**Warning:** Must run pytest from packages/erk-shared/ directory OR use separate test commands with proper working directory context. Running from root causes ModuleNotFoundError due to incorrect import resolution for package tests.

**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire is critical because the error message (ModuleNotFoundError) doesn't indicate that changing the working directory is the solution. Developers may waste time attempting to fix imports, add __init__.py files, or modify the package structure when the simple fix is to run tests from the correct directory. The pattern affects all test files in the packages/erk-shared/tests/ directory, making it a recurring issue for anyone working on the shared package.

## Potential Tripwires

**No items with score 2-3.**

All prevention insights from the session analysis scored either >= 4 (qualified as tripwire) or < 2 (not warranting documentation).

## Implementation Priority

**Recommended implementation order:**

1. **FIRST:** Add package-specific pytest tripwire to docs/learned/testing/tripwires.md (HIGH priority, prevents future errors)
2. **SECOND:** Update docs/learned/planning/next-steps-output.md property tables (HIGH priority, existing doc accuracy)
3. **THIRD:** Add naming convention to docs/learned/conventions.md (MEDIUM priority, establishes principle)
4. **FOURTH:** Create docs/learned/testing/format-function-testing.md (MEDIUM priority, documents new pattern)

**Rationale for ordering:**
- Tripwires prevent future errors (highest impact)
- Existing doc updates maintain accuracy (documentation hygiene)
- New patterns/principles guide future work (forward-looking value)
