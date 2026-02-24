# Documentation Plan: Consolidate PR validation into --stage=impl flag, remove scattered exec scripts

## Context

PR #7987 consolidates scattered PR validation logic by adding a `--stage=impl` flag to the existing `erk pr check` command. Previously, validation logic was duplicated between `erk pr check` (three checks) and `erk exec pr-check-complete` (same three checks plus impl-context cleanup). This duplication violated erk's design principle of having clear, consolidated user-facing commands.

The implementation introduced several architectural improvements: a type-safe `PrCheck` NamedTuple for validation results, LBYL (Look Before You Leap) refactoring of the plan-ref validation logic, and comprehensive test coverage. The workflow documentation (`plan-implement.md`) was updated to use the new `--stage=impl` flag instead of the removed exec script.

The sessions that produced this PR revealed important patterns: recovering deleted plans from git history, detecting false positives in bot reviews, and efficiently addressing batched review comments. These operational insights are as valuable as the technical changes and warrant documentation to prevent future agents from re-learning them.

## Raw Materials

PR #7987 - Session analysis and diff analysis in learn-agents directory

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 13 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 5 |

## Documentation Items

### HIGH Priority

#### 1. Update PR validation rules documentation

**Location:** `docs/learned/pr-operations/pr-validation-rules.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
---
title: PR Validation Rules
read-when: running erk pr check, understanding PR validation behavior, implementing validation commands
tripwires: 1
---

# PR Validation Rules

## Core Checks (Always Run)

Three checks run regardless of stage:

1. **Branch/Issue Agreement** - Branch name contains issue number matching PR title
2. **Closing Reference** - PR body includes "Closes #N" for the plan issue
3. **Checkout Footer** - PR body ends with standard checkout command block

## Stage-Specific Checks

### --stage=impl

When running `erk pr check --stage=impl`, one additional check is performed:

4. **Impl-Context Cleanup** - `.erk/impl-context/` directory must not exist

This check validates that the draft-PR staging area was cleaned up before implementation began (per plan-implement.md Step 2d).

## Usage

```bash
# Default mode: run core checks
erk pr check

# Implementation mode: run core + impl-context cleanup check
erk pr check --stage=impl
```

## When to Use Each Mode

- **Default mode**: Anytime during PR development, quick validation
- **--stage=impl**: Before PR submission in implementation workflows

See `src/erk/cli/commands/pr/check_cmd.py` for implementation details.
```

---

#### 2. Update impl-context documentation

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

Add a "Validation" section after the existing lifecycle documentation:

```markdown
## Validation

### Automated Check

Use `erk pr check --stage=impl` to verify impl-context cleanup before PR submission:

```bash
# Fails if .erk/impl-context/ exists
erk pr check --stage=impl
```

This check is integrated into the plan-implement workflow (Step 13) to catch leaked impl-context before PR submission.

### Prevention Strategies Update

Add to existing prevention strategies:

- **Automated validation**: `erk pr check --stage=impl` validates cleanup before PR submission
- **Workflow integration**: plan-implement.md Step 13 runs validation automatically

See `src/erk/cli/commands/pr/check_cmd.py` for the impl-context check implementation.
```

---

#### 3. Document exec-to-command migration pattern

**Location:** `docs/learned/cli/exec-to-command-migration.md`
**Action:** CREATE
**Source:** [PR #7987] [Impl]

**Draft Content:**

```markdown
---
title: Exec Script to Command Migration
read-when: creating new erk exec scripts, consolidating duplicate validation logic, designing CLI command structure
tripwires: 1
---

# Exec Script to Command Migration

## Decision Framework

Before creating a new `erk exec` script, evaluate whether the logic should be added to an existing user-facing command.

### Consolidate When

- Exec script adds only one additional check to existing command
- Logic is conceptually related to existing command's purpose
- Users would expect the functionality in the existing command
- Example: `pr-check-complete` added impl-context check to `pr check` functionality

### Keep Separate When

- Logic serves fundamentally different purpose
- Target audience is different (internal vs external)
- Workflow isolation is valuable

## Migration Pattern

### Step 1: Add Stage/Mode Flag

Use `click.option("--stage", type=click.Choice([...]))` to add variants:

```python
@click.option("--stage", type=click.Choice(["impl"]), help="Validation stage")
def command(stage: str | None):
    # Core checks always run
    run_core_checks()

    # Stage-specific checks
    if stage == "impl":
        run_impl_checks()
```

### Step 2: Migrate Tests

Move tests from exec script test file to command test file. Click decorators (`@click.pass_obj` vs `@click.pass_context`) work identically with `runner.invoke(cmd, obj=ctx)`.

### Step 3: Update Workflow References

Search for exec script usage in `.claude/commands/` and update to new flag syntax.

### Step 4: Remove Exec Script

Delete script and registration following erk's "no backwards compatibility" principle.

## Example: PR #7987

Consolidated `erk exec pr-check-complete` into `erk pr check --stage=impl`:

- Before: Two commands with 90% duplicate logic
- After: One command with `--stage` flag for impl-specific checks
```

---

#### 4. Bot review line drift tripwire

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add tripwire entry:

```markdown
## Line Number Drift in Bot Reviews

**Trigger:** When bot review comments flag code at specific line numbers

**Warning:** Search file for actual pattern mentioned in comment; line numbers shift after formatting/refactoring commits. Do not trust line numbers blindly.

**Background:** In PR #7987 addressing, bot flagged line 1002 but actual inline import was at line 1048 after formatting commits. Agent correctly used `Grep` to find actual location.

**Correct approach:**
1. Read bot comment for the pattern being flagged (e.g., "inline import json")
2. Search file for that pattern: `Grep(pattern="import json", path="path/to/file.py")`
3. Verify actual location before making changes
```

---

### MEDIUM Priority

#### 5. Document LBYL validation pattern with concrete example

**Location:** `docs/learned/architecture/lbyl-validation-pattern.md`
**Action:** CREATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
---
title: LBYL Validation Pattern
read-when: writing validation functions, refactoring try/except patterns, implementing CLI checks
tripwires: 0
---

# LBYL Validation Pattern

## Anti-Pattern: Try/Except for Control Flow

```python
# WRONG: Using exception for control flow
try:
    result = validate_something()
except ValidationError:
    return False, "Validation failed"
```

## Pattern: Explicit Pre-Checks

```python
# CORRECT: Check conditions before operations
if value is None:
    return PrCheck(passed=False, description="Value not found")
if not meets_condition(value):
    return PrCheck(passed=False, description="Condition not met")
return PrCheck(passed=True, description="Validation passed")
```

## Concrete Example: Plan-Ref Validation

PR #7987 refactored plan-ref validation from try/except to explicit checks.

See `src/erk/cli/commands/pr/check_cmd.py` for the LBYL implementation that:
1. Extracts issue number from branch name (returns None if not found)
2. Reads plan-ref from `.impl/` (returns None if not found)
3. Compares values explicitly
4. Reports specific mismatches or agreement

## Benefits

- Clearer error messages (specific failure reasons)
- Easier debugging (explicit control flow)
- Follows erk coding standards
- Better type checker support (narrowing via None checks)
```

---

#### 6. Document PrCheck NamedTuple pattern

**Location:** `docs/learned/architecture/validation-result-types.md`
**Action:** CREATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
---
title: Validation Result Types
read-when: implementing validation commands, choosing between NamedTuple and discriminated unions, returning structured results
tripwires: 0
---

# Validation Result Types

## NamedTuple for Simple Validation Results

When validation returns pass/fail with a message, use NamedTuple:

```python
from typing import NamedTuple

class PrCheck(NamedTuple):
    passed: bool
    description: str
```

## When to Use NamedTuple vs Discriminated Unions

### Use NamedTuple When

- Simple pass/fail with message
- Results will be collected and iterated
- No complex error type hierarchy needed
- Example: PR validation checks

### Use Discriminated Unions When

- Multiple distinct error types with different data
- Error handling varies by type
- Type narrowing in match statements needed

## Benefits of NamedTuple

- Type-safe: IDE autocomplete, type checker support
- Self-documenting: `check.passed` clearer than `check[0]`
- Composable: Easy to collect in lists and iterate
- Lightweight: No dataclass overhead

See `src/erk/cli/commands/pr/check_cmd.py` for the PrCheck pattern in practice.
```

---

#### 7. Update NamedTuple vs bare tuple guidance

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

Add example to existing conventions:

```markdown
## Structured Return Types

### Use NamedTuple for Multi-Value Returns

```python
# WRONG: Bare tuple obscures meaning
def check_pr() -> tuple[bool, str]:
    return True, "Check passed"

# CORRECT: NamedTuple provides clarity
class PrCheck(NamedTuple):
    passed: bool
    description: str

def check_pr() -> PrCheck:
    return PrCheck(passed=True, description="Check passed")
```

Benefits: Type safety, self-documenting field access (`check.passed` vs `check[0]`), IDE support.

See `src/erk/cli/commands/pr/check_cmd.py` for a production example.
```

---

#### 8. Document git archaeology for deleted plans

**Location:** `docs/learned/planning/git-archaeology.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Git Archaeology for Deleted Plans
read-when: implementing from branch with unclear commits, missing plan context, recovering deleted impl-context
tripwires: 1
---

# Git Archaeology for Deleted Plans

## Problem

Implementation context may be deleted in commits (e.g., "cp" commit that cleans up `.erk/impl-context/`). Without the plan, agents may implement incorrectly.

## Detection

Before implementing from branch context:

```bash
# Check commit history
git log --oneline master..HEAD

# Look for commits that might have deleted impl-context
git log --oneline --all -- '.erk/impl-context/*'
```

## Recovery Pattern

If `.erk/impl-context/` was deleted in a commit:

```bash
# Show the deleted content
git show <commit>:.erk/impl-context/plan.md
git show <commit>:.erk/impl-context/ref.json

# Or view the deletion diff
git show <commit> -- .erk/impl-context/
```

## Real Example

In PR #7987, a "cp" commit deleted the implementation plan. User intervention recovered the plan from git history, which specified:
- `--stage=impl` flag design
- NamedTuple usage for PrCheck
- LBYL refactoring requirements

Without recovery, the agent would have implemented based only on PR review comments, missing critical design decisions.

## Prevention

When starting implementation from a branch:
1. Run `git log master..HEAD` to understand commit history
2. Check if any commits deleted `.erk/impl-context/`
3. If deleted, recover plan from git history before implementing
```

---

#### 9. Document false positive detection workflow

**Location:** `docs/learned/pr-operations/false-positive-handling.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: False Positive Detection Workflow
read-when: addressing bot review comments, handling automated review feedback, resolving threads for already-fixed issues
tripwires: 0
---

# False Positive Detection Workflow

## Pattern

Bot reviews may flag issues that were already fixed in subsequent commits.

### Workflow

1. **Read flagged code**: Check current state at reported line
2. **Verify issue exists**: If code doesn't match bot's description, investigate
3. **Check git history**: Look for commits that may have fixed the issue
4. **Resolve thread**: Include commit reference if already fixed

## Example

Bot flagged inline `import json` at line 1048:

1. Read line 1048 - no inline import found
2. Check module-level imports - `import json` at line 3
3. Check git history - commit a29660a72 removed inline import
4. Resolve thread: "Already fixed in commit a29660a72 - inline import removed, module-level import at line 3 is used"

## Resolution Comment Format

When resolving threads for already-fixed issues:

```
Already fixed in commit <hash> - <brief description of what was fixed>
```

## Key Principle

Always resolve threads even when no code changes are needed. Outdated threads must still be resolved to maintain clean PR state.
```

---

#### 10. Update CLI reference with --stage=impl

**Location:** `docs/learned/cli/erk-exec-commands.md` or create `docs/learned/cli/pr-commands.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
## erk pr check

Validates PR readiness with configurable validation stages.

### Usage

```bash
# Default: run core validation checks
erk pr check

# Implementation stage: run core + impl-specific checks
erk pr check --stage=impl
```

### Options

- `--stage=impl`: Enable implementation-stage validation (adds impl-context cleanup check)

### Checks by Stage

| Check | Default | --stage=impl |
|-------|---------|--------------|
| Branch/Issue Agreement | Yes | Yes |
| Closing Reference | Yes | Yes |
| Checkout Footer | Yes | Yes |
| Impl-Context Cleanup | No | Yes |

See `src/erk/cli/commands/pr/check_cmd.py` for implementation.
```

---

### LOW Priority

#### 11. Add import organization antipattern to testing tripwires

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
## Redundant Inline Imports

**Trigger:** When adding inline imports in test functions

**Warning:** Check if module-level import already exists before adding inline import. Automated review bots flag this as a code quality issue.

**Background:** In PR #7987, bot flagged redundant inline `import json` when module-level import existed. This is a common copy-paste mistake when moving test code.

**Correct approach:**
1. Check file header for existing imports
2. Use module-level import if available
3. Only use inline import when truly needed for lazy loading
```

---

#### 12. Document batch thread resolution pattern

**Location:** `docs/learned/pr-operations/` (add to existing patterns doc)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Batch Thread Resolution

Use `erk exec resolve-review-threads` (plural) with JSON array via stdin for multi-thread resolution:

```bash
echo '[{"thread_id": "123", "comment": "Fixed in commit abc"}, {"thread_id": "456", "comment": "Already addressed"}]' | erk exec resolve-review-threads
```

More efficient than repeated single-thread calls when addressing multiple review comments.
```

---

#### 13. Document stage-based validation pattern

**Location:** `docs/learned/cli/plan-implement.md`
**Action:** UPDATE
**Source:** [PR #7987]

**Draft Content:**

```markdown
## Stage-Based Validation

Commands can support multiple validation stages via `--stage` flag:

```python
@click.option("--stage", type=click.Choice(["impl", "review"]))
```

### Benefits

- Single command serves multiple workflow phases
- Clear separation of stage-specific checks
- Extensible to future stages without new commands

### Example

`erk pr check` supports:
- Default: Core PR validation
- `--stage=impl`: Core + implementation cleanup validation
```

---

## Stale Documentation Cleanup

No stale documentation detected. All existing docs contain valid file references.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Command Duplication

**What happened:** Created `erk exec pr-check-complete` when `erk pr check` already existed and could be extended.

**Root cause:** Exec scripts were easier to create than modifying existing commands. No design review caught the duplication.

**Prevention:** Before adding exec scripts, grep for existing commands with similar names/purposes and evaluate consolidation.

**Recommendation:** TRIPWIRE

### 2. Starting Without Full Context

**What happened:** Agent began implementing based on PR review comments alone, missing the actual implementation plan that had been deleted.

**Root cause:** User's "cp" commit deleted `.erk/impl-context/plan.md` before agent started.

**Prevention:** Always check `git log` for deleted `.erk/impl-context/` commits when branch context seems unclear.

**Recommendation:** TRIPWIRE

### 3. Missing Plan Context from Deleted Files

**What happened:** Implementation plan contained critical design decisions (NamedTuple, LBYL, --stage flag) that would have been missed.

**Root cause:** Plan was deleted as part of routine cleanup, but agent started implementing before plan was reviewed.

**Prevention:** Recover plan from git history before implementing.

**Recommendation:** TRIPWIRE (covered by #2)

### 4. Line Number Mismatch in Bot Reviews

**What happened:** Bot flagged line 1002 but actual issue was at line 1048 after formatting commits.

**Root cause:** Code formatting shifted line numbers between bot scan and human review.

**Prevention:** Search file for actual pattern mentioned in bot comment; don't trust line numbers blindly.

**Recommendation:** TRIPWIRE

### 5. False Positive Bot Reviews

**What happened:** Bot flagged inline import that had already been fixed in prior commit.

**Root cause:** Bot comments lag behind actual code state.

**Prevention:** Always read current code state and check git history before making changes.

**Recommendation:** ADD_TO_DOC (false-positive-handling.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Bot Review Line Number Drift

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)

**Trigger:** When addressing bot review comments that reference specific line numbers

**Warning:** Search file for actual pattern mentioned in comment; line numbers shift after formatting/refactoring commits. Do not trust line numbers blindly.

**Target doc:** `docs/learned/pr-operations/tripwires.md`

This is tripwire-worthy because agents will naturally go to the reported line number, waste time investigating code that doesn't match the bot's description, and may make incorrect changes if they assume the line number is authoritative. The PR #7987 session showed the correct recovery pattern: use Grep to find the actual pattern location.

### 2. Git Archaeology for Deleted Plans

**Score:** 6/10 (Non-obvious +2, Destructive potential +2, Cross-cutting +2)

**Trigger:** Before implementing from branch context when commit history includes unclear commits (especially "cp" commits)

**Warning:** Run `git log master..HEAD` and check if `.erk/impl-context/` was deleted in any commit; recover plan from git history before implementing.

**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because implementing without the original plan leads to incorrect or incomplete implementations. In PR #7987, user intervention was required to prevent wrong implementation. Without the plan, the agent would have missed the NamedTuple requirement, LBYL refactoring, and --stage flag design.

### 3. Command Duplication Detection

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +1, Non-obvious +1)

**Trigger:** Before creating new `erk exec` scripts

**Warning:** Grep for existing user-facing commands with similar names/purposes and evaluate consolidation. Adding a flag to an existing command provides better UX than creating a new exec script.

**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because the natural path of least resistance is to create a new exec script rather than extend an existing command. PR #7987 required consolidation of duplicate logic that should have been caught during initial design.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. False Positive Bot Reviews

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Caught by defensive reading practice, but not destructive enough for full tripwire. Better served by documentation in false-positive-handling.md with concrete examples.

### 2. Import Organization Antipattern

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)

**Notes:** Caught by automated review bots. Low impact since it's a style issue, not a correctness issue. Adding to testing tripwires as a reminder is sufficient.

### 3. Outdated Thread Resolution

**Score:** 2/10 (Cross-cutting +2)

**Notes:** Already documented in /erk:pr-address command. The sessions provided good examples but the principle is already established.

### 4. Starting Without Full Context

**Score:** 3/10 (Destructive potential +2, Non-obvious +1)

**Notes:** Covered by git archaeology tripwire (#2 above). This is the general case; the git archaeology tripwire is the specific actionable check.

### 5. Missing Plan Context from Deleted Files

**Score:** 3/10 (Destructive potential +2, Silent failure +1)

**Notes:** Covered by git archaeology tripwire (#2 above). Same pattern, same prevention.
