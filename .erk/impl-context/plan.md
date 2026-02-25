# Documentation Plan: Fix learn plan PRs being auto-closed when ephemeral base branch deleted

## Context

This PR addresses a critical workflow bug where learn plan PRs were silently closed by GitHub. The root cause was a coordination failure between three systems: the learn workflow (`learn.yml`) creates temporary `learn/XXXX` branches, `plan-save` used these branches as PR base refs, and GitHub automatically closes PRs when their base branch is deleted. When the learn workflow cleaned up ephemeral branches, all associated PRs vanished.

The implementation session was remarkably clean - the plan was well-researched and included the exact fix needed (a 4-line conditional check to detect `learn/` prefixes and use trunk instead). The agent followed the complete lifecycle (signal started, implement, signal ended, CI, submit, signal submitted) without user intervention. The subsequent review response session demonstrated mature PR workflow handling, including an iteration through type narrowing challenges that produced valuable documentation insights.

The key learnings from this implementation are cross-cutting: ephemeral branch detection is a pattern that will apply to any future workflow-managed temporary branches (e.g., `tmp/`, `scratch/`), and the Python type narrowing limitation with extracted boolean variables applies across any codebase using strict type checking. These insights deserve prominent documentation to prevent future developers from rediscovering these patterns the hard way.

## Raw Materials

PR #8178

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 11 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 1 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. learn-workflow.md phantom reference

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/submit.py`
**Cleanup Instructions:** Replace references to `src/erk/cli/commands/submit.py` with `src/erk/cli/commands/pr/dispatch_cmd.py`. The submit.py file was reorganized into the pr/ subdirectory.

### 2. learn-vs-implementation-plans.md phantom reference

**Location:** `docs/learned/planning/learn-vs-implementation-plans.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/submit.py`
**Cleanup Instructions:** Replace references to `src/erk/cli/commands/submit.py` with `src/erk/cli/commands/pr/dispatch_cmd.py`.

### 3. lifecycle.md phantom reference

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/submit.py`
**Cleanup Instructions:** Replace function reference `get_learn_plan_parent_branch()` to point to `src/erk/cli/commands/pr/dispatch_cmd.py`.

## Documentation Items

### HIGH Priority

#### 1. GitHub PR auto-close on deleted base branch

**Location:** `docs/learned/architecture/github-pr-autoclose.md`
**Action:** CREATE
**Source:** [Impl] [PR #8178]

**Draft Content:**

```markdown
---
title: GitHub PR Auto-Close on Deleted Base Branch
read_when:
  - "creating PRs from workflow-managed branches"
  - "deleting branches that may be PR base refs"
  - "debugging why PRs were unexpectedly closed"
tripwires:
  - action: "deleting a branch used as a PR base"
    warning: "Verify all PRs targeting this branch have landed or been retargeted. GitHub automatically closes PRs when their base branch is deleted."
---

# GitHub PR Auto-Close on Deleted Base Branch

GitHub automatically closes pull requests when their base branch is deleted. This behavior is distinct from issue auto-close (documented in `github-issue-autoclose.md`).

## The Behavior

When a branch used as a PR's base ref is deleted:
1. GitHub closes all PRs targeting that branch
2. Closure is asynchronous (may take 1-3 seconds)
3. No warning is issued before deletion
4. PRs can be recovered by retargeting to a new base

## Why This Matters

Workflows that create temporary branches (e.g., learn workflow's `learn/XXXX` branches) must never use those branches as PR base refs. If a PR is created targeting an ephemeral branch, and the workflow later deletes that branch, the PR is lost.

## Recovery Options

- **Before deletion**: Retarget the PR to a persistent branch (trunk or feature branch)
- **After deletion**: The PR is closed but can be reopened with a new base via `gh pr edit --base <new-base>`

## Prevention Strategies

1. Detect ephemeral branch prefixes (e.g., `learn/`, `tmp/`) and use trunk as base instead
2. Defer branch deletion until all targeting PRs have landed
3. Use naming conventions that clearly mark ephemeral branches

## Related Documentation

- `github-issue-autoclose.md`: Issue auto-close behavior (different mechanism)
- `docs/learned/planning/ephemeral-branches.md`: Ephemeral branch detection pattern
```

---

#### 2. Ephemeral branches concept

**Location:** `docs/learned/planning/ephemeral-branches.md`
**Action:** CREATE
**Source:** [Impl] [PR #8178]

**Draft Content:**

```markdown
---
title: Ephemeral Branches
read_when:
  - "implementing workflows that create temporary branches"
  - "adding new branch prefix patterns"
  - "working with learn workflow branches"
  - "debugging PR creation from workflow branches"
tripwires:
  - action: "creating PRs from workflow-managed branches"
    warning: "Check if branch is ephemeral (learn/, tmp/, scratch/). Use trunk as base instead of ephemeral branch. GitHub auto-closes PRs when base branch is deleted."
---

# Ephemeral Branches

Ephemeral branches are temporary, workflow-managed branches that are deleted after their purpose is fulfilled. They require special handling in PR creation to prevent GitHub from auto-closing PRs.

## Definition

An ephemeral branch is:
- Created by an automated workflow
- Deleted as part of workflow cleanup
- Not intended to persist as a feature branch

## Known Ephemeral Branch Prefixes

| Prefix | Workflow | Purpose |
|--------|----------|---------|
| `learn/` | Learn workflow | Houses learn plan execution, deleted after PR creation |

## The Problem

When `plan-save` creates a PR, it normally uses the current branch as the base ref (for stacking). However, if the current branch is ephemeral, two problems occur:

1. The PR targets a branch that will be deleted
2. GitHub auto-closes PRs when their base branch is deleted

## The Solution

`plan-save` detects ephemeral branch prefixes and uses trunk as the base ref instead. See `src/erk/cli/commands/exec/scripts/plan_save.py` for implementation.

## Adding New Ephemeral Prefixes

When adding a new workflow with temporary branches:
1. Choose a distinctive prefix (e.g., `tmp/`, `scratch/`)
2. Update the ephemeral branch detection logic in `plan_save.py`
3. Document the prefix in this file

## Cross-References

- `docs/learned/architecture/github-pr-autoclose.md`: Why base branch deletion closes PRs
- `.github/workflows/learn.yml`: Learn workflow branch cleanup
```

---

#### 3. Type narrowing with extracted boolean variables

**Location:** `docs/learned/architecture/type-narrowing-patterns.md`
**Action:** CREATE
**Source:** [Impl] [PR #8178]

**Draft Content:**

```markdown
---
title: Type Narrowing Patterns
read_when:
  - "extracting boolean conditions to variables"
  - "working with Optional types and type narrowing"
  - "debugging 'invalid-argument-type' errors after refactoring"
tripwires:
  - action: "extracting `is not None` check to boolean variable"
    warning: "Type narrowing only works when condition is inline in if/while statement. Extracting to boolean prevents type checker from narrowing `T | None` to `T`."
---

# Type Narrowing Patterns

Python type checkers (pyright, mypy) can narrow types based on control flow, but this narrowing has important limitations.

## The Limitation

Type narrowing only works when the `is not None` check appears directly in the control flow statement. Extracting the check to a boolean variable breaks narrowing.

## Failing Pattern

```python
# This does NOT work for type narrowing
current_branch: str | None = get_branch()
is_valid = current_branch is not None and current_branch.startswith("feature/")

if is_valid:
    # Type checker still sees current_branch as str | None
    do_something(current_branch)  # ERROR: invalid-argument-type
```

## Working Pattern

```python
# This works - condition is inline
current_branch: str | None = get_branch()

if current_branch is not None and current_branch.startswith("feature/"):
    # Type checker narrows current_branch to str
    do_something(current_branch)  # OK
```

## Why This Happens

Type checkers track type refinements through control flow statements (if, while, match). When you extract a condition to a boolean variable, the type checker cannot prove that the boolean's value correlates with the original type check.

## Multi-Line Conditions

When inlining creates lines too long for style limits, use parenthesized multi-line conditions:

```python
if (
    current_branch is not None
    and current_branch.startswith("feature/")
    and some_other_condition
):
    do_something(current_branch)
```

## Related

This pattern was discovered during PR #8178 when a code review suggested inlining a single-use variable, which then required restructuring for type narrowing.
```

---

### MEDIUM Priority

#### 4. Plan-save PR base selection logic

**Location:** `docs/learned/planning/plan-save.md`
**Action:** UPDATE (or CREATE if doesn't exist)
**Source:** [Impl] [PR #8178]

**Draft Content:**

```markdown
## PR Base Branch Selection

The `_save_as_planned_pr` function in `plan_save.py` selects the PR base branch using a three-path decision tree:

### Path 1: Ephemeral Branches -> Use Trunk

If the current branch is ephemeral (e.g., starts with `learn/`), the PR base is set to trunk. This prevents GitHub from auto-closing the PR when the ephemeral branch is deleted by workflow cleanup.

### Path 2: Feature Branches -> Stack on Current

If on a feature branch (not trunk, not detached, not ephemeral), the PR is stacked on the current branch. This supports feature branch workflows where multiple PRs build on each other.

### Path 3: Trunk or Detached HEAD -> Use Trunk

If on trunk or in detached HEAD state, the PR base is trunk. This is the default behavior for standalone PRs.

### Implementation Reference

See `src/erk/cli/commands/exec/scripts/plan_save.py`, grep for `_save_as_planned_pr` to find the branch selection logic.
```

---

#### 5. Lifecycle signaling workflow

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE_EXISTING
**Source:** [Impl]

**Draft Content:**

```markdown
## Lifecycle Signaling Workflow

The implementation lifecycle follows a structured signaling pattern:

1. **started**: Signals implementation has begun (`erk exec impl-signal started`)
2. **ended**: Signals implementation complete (`erk exec impl-signal ended`)
3. **submitted**: Signals PR submitted (`erk exec impl-signal submitted`)

Each signal updates the plan issue's metadata block to track progress. The learn workflow demonstrated clean execution of this complete lifecycle without user intervention.

### Signal Coordination

- `started` must be called before any code changes
- `ended` must be called after all tests pass
- `submitted` is called after `erk pr submit` succeeds

### Verification

Run `erk pr check --stage=impl` after submission to verify the PR was created correctly.
```

---

#### 6. PR review thread batch resolution

**Location:** `docs/learned/pr-operations/thread-resolution.md`
**Action:** CREATE (or UPDATE if exists)
**Source:** [Impl] [PR #8178]

**Draft Content:**

```markdown
---
title: PR Review Thread Resolution
read_when:
  - "resolving PR review threads programmatically"
  - "using erk exec resolve-review-threads"
---

# PR Review Thread Resolution

The `erk exec resolve-review-threads` command resolves multiple review threads in a single operation.

## Usage

Provide thread IDs as JSON via stdin:

```bash
echo '{"thread_ids": ["PRRT_123", "PRRT_456"]}' | erk exec resolve-review-threads
```

## Single Thread Resolution

For resolving a single thread after addressing feedback:

```bash
echo '{"thread_ids": ["PRRT_kwDPAB..."]}' | erk exec resolve-review-threads
```

## Workflow Integration

The typical PR review workflow:
1. Load `pr-operations` skill for context
2. Classify feedback with pr-feedback-classifier subagent
3. Apply fixes locally
4. Commit changes
5. Resolve threads using batch command
6. Run CI iteration
7. Push final changes

This pattern was demonstrated successfully in PR #8178 review response.
```

---

#### 7. GitHub CLI field name quirks

**Location:** `docs/learned/architecture/github-cli-quirks.md`
**Action:** UPDATE_EXISTING
**Source:** [Impl]

**Draft Content:**

```markdown
## Field Name Inconsistencies

GitHub CLI field names are not always intuitive. Common gotchas:

| Intuitive Name | Actual Field | Context |
|----------------|--------------|---------|
| `draft` | `isDraft` | `gh pr view --json` |

### Prevention

Before using `gh` command with `--json` output:
1. Check available fields with `gh pr view --help` or `gh api --help`
2. Test the query interactively before scripting
3. Use `gh pr view --json fieldName` to verify field exists

### Example

```bash
# Wrong - field doesn't exist
gh pr view --json draft

# Correct
gh pr view --json isDraft
```
```

---

### LOW Priority

#### 8. Tiered testing approach

**Location:** `docs/learned/testing/testing-strategies.md`
**Action:** UPDATE_EXISTING (if section doesn't exist)
**Source:** [Impl]

**Draft Content:**

```markdown
## Tiered Testing for Confidence Building

When implementing focused changes, use a tiered testing approach:

1. **Specific test file first**: Run tests in the most relevant file (e.g., `test_plan_save.py` for plan-save changes)
2. **Broader suite second**: Run the full test suite to catch regressions

Example from PR #8178:
- First: 20 tests in specific file (fast feedback)
- Then: 1035 tests in full suite (regression check)

This approach provides quick feedback during development while ensuring no regressions before submission.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. GitHub auto-closes PRs when base branch deleted

**What happened:** Learn plan PRs were silently closed after the learn workflow completed and cleaned up ephemeral branches.
**Root cause:** Using ephemeral `learn/XXXX` branches as PR base refs without exclusion logic.
**Prevention:** Add prefix checks (e.g., `startswith("learn/")`) to exclude temporary branches from base ref selection.
**Recommendation:** TRIPWIRE (score 7/10)

### 2. Type narrowing failure with extracted boolean

**What happened:** After inlining a boolean variable per code review, the type checker reported `invalid-argument-type`.
**Root cause:** Type checkers cannot track type refinement through intermediate boolean variables.
**Prevention:** Keep `is not None` checks directly in if/while conditions; avoid extracting to boolean variables.
**Recommendation:** TRIPWIRE (score 6/10)

### 3. Wrong GitHub CLI field names

**What happened:** Used `--json draft` instead of `--json isDraft` for PR queries.
**Root cause:** GitHub CLI field naming doesn't match intuitive expectations.
**Prevention:** Always check `gh` command help or test queries before using in scripts.
**Recommendation:** ADD_TO_DOC (low severity, easy to debug)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Ephemeral branch PR base exclusion

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, External tool quirk +1)
**Trigger:** Before creating PRs from workflow-managed branches
**Warning:** Check if branch is ephemeral (learn/, tmp/, scratch/) and use trunk as base instead. GitHub auto-closes PRs when base branch is deleted.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire addresses a silent failure mode where work appears lost when PRs are auto-closed. The pattern is cross-cutting because any future workflow with temporary branches will need the same exclusion logic. Without this tripwire, developers will rediscover this GitHub behavior the hard way.

### 2. Type narrowing with extracted booleans

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before extracting `is not None` check to boolean variable
**Warning:** Type narrowing only works when condition is inline in if/while statement. Extracting to boolean prevents type checker from narrowing `T | None` to `T`.
**Target doc:** `docs/learned/architecture/tripwires.md`

This Python type system limitation is not obvious to developers. The code works at runtime but fails type checking, which can cause CI failures and confusion. This pattern applies anywhere strict type checking is used with optional types.

### 3. GitHub PR auto-close on deleted base

**Score:** 6/10 (Non-obvious +2, Destructive potential +2, External tool quirk +1, Silent failure +1)
**Trigger:** Before deleting a branch that is used as a PR base ref
**Warning:** Verify all PRs targeting this branch have landed or been retargeted. GitHub automatically closes PRs when base branch is deleted.
**Target doc:** `docs/learned/erk/tripwires.md`

This tripwire warns at deletion time rather than PR creation time. It's a complementary safeguard to the ephemeral branch detection - even if detection is missed at PR creation, this warning can catch the problem before branch deletion.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. GitHub CLI field naming inconsistency

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Low severity because the error is easily debugged - the field simply doesn't exist. The fix is straightforward (check `--help` or test query). Could be promoted if multiple instances of this pattern are encountered across different gh commands.

## Recommended Documentation Order

Based on priority and dependencies:

1. **FIRST**: Fix phantom references in learn-workflow.md, learn-vs-implementation-plans.md, lifecycle.md
2. **SECOND**: Create docs/learned/architecture/github-pr-autoclose.md (foundation for understanding ephemeral branch issue)
3. **THIRD**: Create docs/learned/planning/ephemeral-branches.md (core new concept, depends on #2)
4. **FOURTH**: Add tripwires to planning/tripwires.md, architecture/tripwires.md, erk/tripwires.md
5. **FIFTH**: Create docs/learned/architecture/type-narrowing-patterns.md (standalone architecture pattern)
6. **SIXTH**: Update plan-save.md with three-path selection logic (builds on ephemeral-branches.md)
7. **SEVENTH**: Update lifecycle.md with signaling workflow (cross-references previous docs)
8. **EIGHTH**: Create or update pr-operations/ documentation with thread resolution example
9. **NINTH**: Update github-cli-quirks.md with field naming section
10. **TENTH**: Update testing documentation with tiered testing pattern (optional, lowest priority)
