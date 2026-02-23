# Documentation Plan: Convert submit pipeline to git plumbing and wire configurable plan backend

## Context

This implementation converted the submit pipeline from a checkout-based workflow to git plumbing operations, fundamentally changing how erk creates commits on plan branches. The core motivation was eliminating race conditions when multiple Claude Code sessions share a worktree: the old approach checked out plan branches, staged files, committed, and restored the original branch - creating windows where concurrent sessions could conflict. The new approach uses `commit_files_to_branch` to write commits directly to refs without touching the working tree.

The architectural shift required a new helper function (`build_impl_context_files`) that generates impl-context file contents as an in-memory dict instead of writing to the filesystem. This enables plumbing operations throughout the submit pipeline. The refactoring also eliminated the `branch_rollback` context manager that had provided cleanup-on-failure semantics - now unnecessary since plumbing commits are atomic and don't modify working tree state.

Documentation is critical here because the git plumbing vs porcelain decision framework establishes patterns for all future git operations in erk. Future agents need to understand when to use `commit_files_to_branch` (race-free, atomic) versus checkout-based operations (Graphite requires checkout for stack context). The implementation also reinforced important terminology conventions: "plan" is provider-agnostic while "issue" is GitHub-specific, and commit messages should use plan-centric language.

## Raw Materials

PR #7972

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 19    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 6     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Git Plumbing vs Porcelain Decision Framework

**Location:** `docs/learned/architecture/git-plumbing-patterns.md`
**Action:** CREATE
**Source:** [Impl] Sessions 186bee4d parts 1-3, [PR #7972]

**Draft Content:**

```markdown
---
read-when:
  - implementing git operations that modify branches
  - working with commit_files_to_branch
  - deciding between checkout-based and plumbing-based git workflows
tripwires: 3
---

# Git Plumbing vs Porcelain Decision Framework

## Overview

Erk provides two approaches for creating commits on branches:

1. **Plumbing (preferred)**: Use `commit_files_to_branch` to write commits directly to refs without touching the working tree
2. **Porcelain**: Checkout branch, stage files, commit, restore original branch

## When to Use Plumbing

Use `commit_files_to_branch` when:
- Creating impl-context commits on plan branches
- Multiple Claude Code sessions might share the worktree
- Operations should be atomic without working-tree side effects
- Creating empty commits (pass `files={}`)

See `src/erk/cli/commands/submit.py` for usage examples (grep for `commit_files_to_branch`).

## When to Use Porcelain (Checkout-Based)

Use checkout-based operations when:
- Graphite operations require current stack context (`gt submit` operates on checked-out branch)
- User-facing operations where working-tree state should intentionally change

## Hybrid Pattern (Graphite Linking)

When Graphite linking is needed:
1. Use plumbing for the commit (no race condition)
2. Wrap only Graphite operations in targeted checkout scope
3. Immediately restore original branch
4. Graphite-free workflows have zero checkouts

## Race Condition Elimination

The checkout-based workflow had failure modes:
- Session A checkouts plan branch
- Session B also tries to checkout → conflict
- Session A fails mid-commit → inconsistent state, rollback needed

Plumbing operations eliminate these issues by never modifying working tree state.

## Empty Commits

Create empty commits (equivalent to `git commit --allow-empty`) via:

```python
ctx.git.commit.commit_files_to_branch(
    repo.root,
    branch=branch_name,
    files={},  # Empty dict = empty commit
    message="...",
)
```
```

---

#### 2. Submit Pipeline Implementation Update

**Location:** `docs/learned/cli/pr-submit-pipeline.md`
**Action:** UPDATE
**Source:** [Impl] Session 186bee4d parts 1-3, [PR #7972]

**Draft Content:**

```markdown
## Implementation Details (Updated)

### Plumbing-Based Architecture

The submit pipeline now uses git plumbing operations instead of checkout-stage-commit:

- `_create_branch_and_pr()` uses `commit_files_to_branch` with files from `build_impl_context_files()`
- `_submit_single_issue()` no longer uses `branch_rollback` context manager
- "branch-exists-but-no-PR" path uses `commit_files_to_branch(files={})` for empty commits
- Graphite linking remains checkout-based but wrapped in minimal targeted scope
- 4+ checkout operations eliminated from critical path

### Key Functions

- `_create_branch_and_pr()`: Creates plan branch with impl-context commit, optionally links via Graphite
- `_submit_single_issue()`: Orchestrates submission for issue-based plans
- `build_impl_context_files()`: Returns impl-context content as `dict[str, str]` for plumbing commits

### Removed Infrastructure

- `branch_rollback()` context manager: No longer needed since plumbing commits are atomic
```

---

#### 3. Plumbing Commit Testing Patterns

**Location:** `docs/learned/testing/plumbing-commit-testing.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 3, [PR #7972]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for git plumbing operations
  - testing commit_files_to_branch usage
  - verifying no checkout occurred in tests
tripwires: 2
---

# Plumbing Commit Testing Patterns

## Overview

When testing code that uses `commit_files_to_branch`, verify both positive assertions (commit structure) and negative assertions (no checkouts).

## Positive Assertions: Verify Commit Structure

Check `fake_git.branch_commits` for commit details:

```python
assert len(git.branch_commits) == 1
branch_commit = git.branch_commits[0]
assert branch_commit.branch == expected_branch
assert branch_commit.files[".erk/impl-context/plan.md"] == expected_content
```

See `tests/commands/plan/test_submit.py` for `test_submit_issue_plan_uses_plumbing_commit`.

## Negative Assertions: Verify No Checkouts

Filter `checked_out_branches` and assert empty:

```python
plan_branch_checkouts = [
    branch for _, branch in fake_git.checked_out_branches
    if branch.startswith("P42-")
]
assert len(plan_branch_checkouts) == 0
```

## Test Environment Selection

- Use `erk_inmem_env` for plumbing tests (no filesystem operations needed)
- Use `erk_isolated_fs_env` only when testing filesystem-based code

## Test Migration Pattern

When converting filesystem-based tests to plumbing-based:
1. Replace filesystem assertions with `branch_commits` structure checks
2. Add no-checkout assertions
3. Rename test to reflect new behavior (e.g., `uses_plumbing_commit` not `cleans_up_folder`)
```

---

#### 4. Plan-Centric Terminology Standards

**Location:** `docs/learned/planning/terminology-standards.md`
**Action:** CREATE
**Source:** [Impl] Sessions 0ad0ce87, f1f5039a, [PR #7972 comments]

**Draft Content:**

```markdown
---
read-when:
  - writing commit messages for plan-related operations
  - creating user-facing strings about plans
  - working with plan backends
tripwires: 1
---

# Plan-Centric Terminology Standards

## Core Principle

Plans are backend-agnostic. Commit messages and user-facing strings should not leak backend implementation details.

## Correct Terminology

| Use This | Not This | Why |
|----------|----------|-----|
| "plan #N" | "issue #N" | Plan is provider-agnostic |
| "plan ID" | "issue number" | Abstracts away GitHub specifics |
| "Add plan #7972" | "Add plan for issue #7972" | Cleaner, provider-neutral |
| `plan_id` | `issue_number` | Field naming convention |

## When Backend-Specific Terms ARE Appropriate

Use provider-specific terms when:
- Error messages specifically about GitHub API failures
- Cross-references in PR bodies that link to GitHub resources
- Internal code that explicitly operates on GitHub issues

## Examples

Commit messages:
- Correct: `"[erk-plan] Add plan #7972"`
- Incorrect: `"[erk-plan] Add plan for issue #7972"`

The parallel draft-PR path uses: `f"Add plan for PR #{plan_number}"` - here "PR" is acceptable because draft-PR is a distinct backend type.
```

---

#### 5. `build_impl_context_files()` Function Documentation

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE (add new section)
**Source:** [Impl] Session 186bee4d parts 1, 5, [PR #7972]

**Draft Content:**

```markdown
## In-Memory Content Generation: `build_impl_context_files()`

For git plumbing operations, use `build_impl_context_files()` instead of `create_impl_context()`.

### Purpose

Returns impl-context file contents as an in-memory `dict[str, str]` for use with `commit_files_to_branch`. No filesystem I/O occurs.

### Usage

```python
from erk_shared.impl_context import build_impl_context_files

files = build_impl_context_files(
    plan_content=plan_markdown,
    plan_id=str(issue_number),
    url=plan_url,
    provider="github-issue",
    objective_id=objective_id,
    now_iso=datetime.now(UTC).isoformat(),
)
# files = {".erk/impl-context/plan.md": ..., ".erk/impl-context/ref.json": ...}

ctx.git.commit.commit_files_to_branch(repo.root, branch=branch, files=files, message=msg)
```

### Relationship to `create_impl_context()`

Both functions produce identical content structure. `create_impl_context()` writes to filesystem; `build_impl_context_files()` returns a dict for plumbing operations.

See `packages/erk-shared/src/erk_shared/impl_context.py` for implementation.

## Idempotency Guarantee

`setup-impl-from-issue` is idempotent: when `.impl/` already exists, it skips branch setup and returns success. Safe to re-execute during development.
```

---

#### 6. Import Cleanup Verification Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add new tripwire)
**Source:** [Impl] Session 186bee4d part 2

**Draft Content:**

```markdown
## Import Cleanup After Partial Refactoring

**Trigger:** Before removing imports after refactoring one code path

**Warning:** Use `Grep` to verify usage across ALL code paths, not just the refactored path.

**Context:** Submit pipeline has dual paths (issue-based vs draft-PR). After refactoring the issue path to use plumbing, some imports may still be needed by the draft-PR path.

**Prevention:**
1. Grep for each import symbol across the entire file
2. Check both conditional branches and alternative execution paths
3. Only remove imports verified unused in ALL paths
```

---

### MEDIUM Priority

#### 7. Phased Refactoring Implementation Pattern

**Location:** `docs/learned/refactoring/phased-implementation.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d parts 1-2

**Draft Content:**

```markdown
---
read-when:
  - planning large refactorings
  - converting patterns across multiple callers
  - removing infrastructure (context managers, utilities)
---

# Phased Refactoring Implementation Pattern

## Overview

Break large refactorings into phases for atomic commits, easier review, and rollback-friendly changes.

## Phase Structure

1. **Add helper**: Create new helper function alongside old implementation
2. **Refactor primary caller**: Update the main code path to use new helper
3. **Refactor secondary callers**: Update remaining callers
4. **Remove old implementation**: Delete unused functions, context managers
5. **Update tests**: Rewrite tests to match new behavior

## Benefits

- Each phase produces a working commit
- Review is scoped and focused
- Rollback is granular (revert specific phase)
- Tests remain passing between phases

## Example: Plumbing Conversion

1. Added `build_impl_context_files` helper
2. Refactored `_create_branch_and_pr` to use it
3. Refactored branch-exists-but-no-PR path
4. Removed `branch_rollback` context manager
5. Updated tests to verify plumbing commits instead of filesystem cleanup
```

---

#### 8. Context Manager Removal Test Migration

**Location:** `docs/learned/refactoring/context-manager-removal.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 3

**Draft Content:**

```markdown
---
read-when:
  - removing context managers that provided rollback/cleanup
  - updating tests after infrastructure removal
---

# Context Manager Removal Test Migration

## When Removing Context Managers

When removing rollback/cleanup context managers, find and update tests asserting on their behavior.

## Test Update Pattern

1. **Find affected tests**: Grep for context manager name in test files
2. **Rename tests**: Update names to reflect new behavior (e.g., `test_rollback_on_failure` -> `test_failure_leaves_original_branch_intact`)
3. **Remove cleanup assertions**: Delete assertions about cleanup messages or state restoration
4. **Keep error assertions**: Verify the error still occurs, but no cleanup happens

## Example

Before: `test_submit_rollback_on_push_failure` asserted "Operation failed, restoring original branch" message
After: `test_submit_push_failure_leaves_original_branch_intact` verifies push fails but no checkout or rollback occurs
```

---

#### 9. Docstring Maintenance During Refactoring

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 2

**Draft Content:**

```markdown
---
read-when:
  - refactoring function implementations
  - removing context managers or changing patterns
tripwires: 1
---

# Refactoring Tripwires

## Docstring Maintenance

**Trigger:** When changing implementation patterns (context managers, checkout -> plumbing)

**Warning:** Update function docstrings immediately. Stale references to removed patterns mislead future developers.

**Prevention:** When editing function implementation, check if docstring describes the old pattern. Update both in the same commit.

## Example

After removing `branch_rollback` context manager, update docstrings that referenced it - e.g., "Uses branch_rollback for cleanup on failure" becomes "Uses plumbing commits (atomic, no working-tree side effects)".
```

---

#### 10. FakeGit Checkout Tracking Test Pattern

**Location:** `docs/learned/testing/fake-git-patterns.md`
**Action:** UPDATE (add section)
**Source:** [Impl] Session 186bee4d part 3

**Draft Content:**

```markdown
## No-Checkout Assertions

When testing plumbing operations, verify no checkout occurred.

### Accessing Checkout History

```python
# When use_graphite=False, ctx.branch_manager is GitBranchManager wrapping FakeGit
# Checkouts tracked in fake_git.checked_out_branches as list of (path, branch) tuples

plan_branch_checkouts = [
    branch for _, branch in fake_git.checked_out_branches
    if branch.startswith("P42-")
]
assert len(plan_branch_checkouts) == 0
```

### Context

`use_graphite=False` -> `ctx.branch_manager` returns `GitBranchManager` wrapping FakeGit. This allows accessing FakeGit's tracking lists (`branch_commits`, `checked_out_branches`) for test assertions.
```

---

#### 11. Review System Architecture

**Location:** `docs/learned/review/local-code-review-workflow.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 4

**Draft Content:**

```markdown
---
read-when:
  - implementing or debugging local code review
  - working with /local:code-review command
---

# Local Code Review Workflow

## Architecture

The local code review system orchestrates parallel review agents with centralized result collection.

## Workflow Phases

1. **Discovery**: `git diff --name-only $(git merge-base master HEAD)...HEAD`
2. **Matching**: Read `.erk/reviews/*.md` frontmatter, match glob patterns to changed files
3. **Execution**: Launch matching reviews in parallel as Task agents with `run_in_background=True`
4. **Collection**: Read scratch files from `.erk/scratch/<run-id>/` after completion
5. **Reporting**: Unified report grouping violations by review

## Review Agent Prompting

Local adaptations from PR-based instructions:
- Replace `gh pr diff` with `git diff $(git merge-base master HEAD)...HEAD`
- Skip PR-interaction steps (posting comments, fetching existing comments)
- Skip review marker checks
- Write findings to scratch file

## Result Validation

Check scratch files exist before reading. Reviews may fail silently if agent doesn't persist results.
```

---

#### 12. Review Definition Schema

**Location:** `docs/learned/review/review-definition-schema.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 4

**Draft Content:**

```markdown
---
read-when:
  - creating new review definitions
  - debugging review matching
---

# Review Definition Schema

## Required Frontmatter

All review files in `.erk/reviews/*.md` must include:

```yaml
---
name: review-name
paths:
  - "**/*.py"  # glob patterns
enabled: true
model: claude-haiku-4-5
marker: "<!-- review-marker -->"
timeout_minutes: 5
---
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Review identifier |
| `paths` | list[string] | Glob patterns for file matching |
| `enabled` | bool | Whether review is active |
| `model` | string | Model ID (claude-haiku-4-5, claude-sonnet-4-5, etc.) |
| `marker` | string | HTML comment marker for PR comments |
| `timeout_minutes` | int | Maximum execution time |

## Glob Pattern Semantics

- `**/*.py` - matches Python files at any depth
- `src/**/*.py` - matches Python files only under src/

## Model Mapping

When launching Task agents:
- `claude-haiku-4-5` -> `haiku`
- `claude-sonnet-4-5` / `claude-sonnet-4-6` -> `sonnet`
```

---

#### 13. Equivalence Testing Pattern

**Location:** `docs/learned/testing/equivalence-testing.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 5

**Draft Content:**

```markdown
---
read-when:
  - creating in-memory analogs of filesystem-based functions
  - maintaining consistency between parallel implementations
---

# Equivalence Testing Pattern

## Purpose

When creating an in-memory version of a filesystem-based function, add an equivalence test to ensure both produce identical output.

## Pattern

```python
def test_inmemory_matches_filesystem():
    # Call in-memory version
    inmem_result = build_impl_context_files(...)

    # Call filesystem version in temp directory
    create_impl_context(temp_path, ...)
    fs_result = {path: (temp_path / path).read_text() for path in expected_paths}

    # Assert equivalence
    assert inmem_result == fs_result
```

## Benefits

- Ensures both implementations stay in sync
- Catches divergence early
- Documents the relationship between functions

## Example

See `tests/packages/erk_shared/test_impl_context.py` for `test_build_impl_context_files_matches_create_impl_context_structure`.
```

---

#### 14. Write vs Edit for Bulk Changes

**Location:** `docs/learned/refactoring/edit-strategies.md`
**Action:** CREATE
**Source:** [Impl] Session 02448556

**Draft Content:**

```markdown
---
read-when:
  - fixing many scattered issues in a single file
  - removing 10+ occurrences of a pattern
---

# Edit Strategies: Write vs Edit

## When to Use Edit

- Small number of focused changes (1-5 locations)
- Changes are isolated and don't risk formatting issues

## When to Use Write

- 10+ scattered changes
- Changes might introduce formatting issues with sequential Edits
- Consolidating patterns (e.g., removing inline imports)

## Pattern for Write

1. Read entire file with Read tool
2. Make all necessary changes in memory
3. Write corrected version with Write tool

## Example

Removing 16+ inline imports: Sequential Edit calls accidentally introduced blank lines. Instead, Read full file, consolidate all imports to module level, Write corrected version.

## Tradeoffs

| Edit | Write |
|------|-------|
| Preserves unrelated formatting | May reformat entire file |
| Shows targeted diff | Shows complete replacement |
| Risk: sequential edits create conflicts | Risk: may cause merge conflicts |
```

---

### LOW Priority

#### 15. Code Review Command Orchestration

**Location:** `docs/learned/commands/local-code-review.md`
**Action:** UPDATE (expand)
**Source:** [Impl] Session 02448556

**Draft Content:**

```markdown
## Implementation Details

### Parallel Task Agent Pattern

Reviews are launched as parallel Task agents with model selection from frontmatter:
- Extract model from frontmatter, map to agent model name
- Launch with `run_in_background=True` for parallelism
- Generate run ID for isolation

### Scratch File Collection

Results collected from `.erk/scratch/<run-id>/<review-name>.md`:
- Wait for all task-notification events before reading
- Verify file exists before reading
- Unified report groups violations by review
```

---

#### 16. Plan Mode Implement-Now Workflow

**Location:** `docs/learned/planning/plan-mode-behavior.md`
**Action:** UPDATE (add section)
**Source:** [Impl] Session f1f5039a

**Draft Content:**

```markdown
## "Skip PR and Implement Here" Option

For small PR iterations that don't need tracking overhead:

### When Appropriate

- Trivial fixes addressing review comments
- Single-line changes
- Changes already covered by existing plan context

### Workflow

1. Agent creates plan in plan mode
2. User chooses "Skip PR and implement here"
3. Agent creates `exit-plan-mode-hook.implement-now` marker
4. Agent exits plan mode, implements directly
5. No plan PR created

### Consideration

After implement-now marker, consider asking if user wants to review plan before proceeding.
```

---

#### 17. Inline Import Anti-Pattern Reinforcement

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (reinforce)
**Source:** [Impl] Session 02448556

**Draft Content:**

```markdown
## Inline Imports in Test Files

**Trigger:** When adding test functions

**Warning:** Use module-level imports at top of file, not inline imports inside function bodies - even if pre-existing pattern uses inline imports.

**Context:** New test functions copied inline import pattern from existing tests, caught by dignified-code-simplifier review.

**Prevention:** Check dignified-python standards before implementing. Don't follow anti-patterns even if they exist in the file.
```

---

#### 18. PR Description Generation with Skills

**Location:** `docs/learned/commands/pr-metadata-generation.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 4

**Draft Content:**

```markdown
---
read-when:
  - generating PR titles and descriptions
  - using erk-diff-analysis skill
---

# PR Metadata Generation with Skills

## Workflow

1. Load `erk-diff-analysis` skill for commit message standards
2. Read skill's reference template (`.claude/skills/erk-diff-analysis/references/commit-message-prompt.md`)
3. Analyze diff file (chunked if large, 200 lines at a time)
4. Write body to temp file first (`/tmp/pr-body-<number>.md`)
5. Apply with `erk exec set-pr-description --title "..." --body-file "..."`

## Benefits

- Consistency across agents and sessions
- Temp file allows verification before applying
- Skill-based templates ensure quality
```

---

#### 19. Review-Driven Test Writing

**Location:** `docs/learned/review/test-coverage-integration.md`
**Action:** CREATE
**Source:** [Impl] Session 186bee4d part 5

**Draft Content:**

```markdown
---
read-when:
  - responding to test-coverage reviewer findings
  - adding unit tests for new functions
---

# Review-Driven Test Writing

## Pattern

When test-coverage reviewer identifies missing tests:
1. Immediately address the finding before other work
2. Write pure unit tests for in-memory functions (no filesystem overhead)
3. Use equivalence testing when function has parallel implementations

## Example

`build_impl_context_files()` flagged by test-coverage reviewer:
- 6 unit tests added verifying dict structure, JSON content
- Final test verifies equivalence with `create_impl_context()` output
- All 20 tests passed on first run
```

---

## Contradiction Resolutions

No contradictions found. Existing documentation aligns with the planned changes.

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced files verified to exist.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Following Existing Anti-Patterns

**What happened:** New test functions copied inline import pattern from existing tests instead of using module-level imports.

**Root cause:** Agent followed existing file patterns without checking coding standards.

**Prevention:** Always use module-level imports for new code, even if existing code uses anti-patterns. Check coding standards before implementing.

**Recommendation:** ADD_TO_DOC (reinforced in testing/tripwires.md)

### 2. Sequential Edits Introducing Formatting Issues

**What happened:** First Edit attempt to remove inline import accidentally introduced blank line.

**Root cause:** Sequential Edit calls near function boundaries can create 3+ blank lines instead of standard 2.

**Prevention:** For scattered changes (10+ locations), use Read full file -> Write complete corrected version pattern instead of sequential Edits.

**Recommendation:** ADD_TO_DOC (new doc: refactoring/edit-strategies.md)

### 3. Test Assertions on Removed Infrastructure

**What happened:** Test `test_submit_rollback_on_push_failure` failed after removing `branch_rollback` context manager.

**Root cause:** Removed infrastructure but didn't update test that checked for its output message.

**Prevention:** When removing context managers or other infrastructure, grep for tests that assert on their behavior.

**Recommendation:** TRIPWIRE (score: 4/10 - cross-cutting, non-obvious)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Plumbing vs Porcelain Decision Framework

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before implementing git operations that modify branches
**Warning:** Use `commit_files_to_branch` (plumbing) for impl-context and multi-session scenarios. Only use checkout-based operations for Graphite linking or user-facing state changes.
**Target doc:** `docs/learned/architecture/git-plumbing-patterns.md`

This is tripwire-worthy because checkout-based operations create race conditions in multi-session environments. The plumbing approach is non-obvious (most developers default to checkout-stage-commit) and cross-cutting (affects all branch-modifying operations).

### 2. Import Cleanup Verification in Dual-Path Code

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before removing imports after refactoring one code path
**Warning:** Use `Grep` to verify usage across ALL code paths, not just the refactored path. Dual-path code (issue vs draft-PR submit) may share imports.
**Target doc:** `docs/learned/architecture/tripwires.md`

This catches a common mistake where imports appear unused after refactoring one branch but are still needed by conditional paths not executed in tests.

### 3. Plumbing Commit Testing (No-Checkout Assertions)

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** When writing tests for git plumbing operations
**Warning:** Always verify BOTH positive (files committed via `branch_commits`) AND negative (no checkouts via `checked_out_branches`) assertions.
**Target doc:** `docs/learned/testing/plumbing-commit-testing.md`

Tests that only check positive outcomes miss regressions where plumbing code accidentally falls back to checkout-based operations.

### 4. Test Migration for Context Manager Removal

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When removing context managers that provided rollback/cleanup
**Warning:** Find and update all tests that assert on rollback behavior. Rename tests to reflect new behavior (error occurs, but no cleanup happens).
**Target doc:** `docs/learned/refactoring/context-manager-removal.md`

Infrastructure removal often leaves zombie test assertions that no longer make sense.

### 5. Docstring Maintenance During Refactoring

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When changing implementation patterns (context managers, checkout -> plumbing)
**Warning:** Update function docstrings immediately when implementation changes. Stale references to removed patterns mislead future developers.
**Target doc:** `docs/learned/refactoring/tripwires.md`

Docstrings that reference removed infrastructure (like `branch_rollback`) create confusion for future agents and developers.

### 6. Plan-Centric Terminology in Commit Messages

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When writing commit messages for plan-related operations
**Warning:** Use "plan #N" not "issue #N" in commit messages. Plans are provider-agnostic; commit messages should not leak backend details.
**Target doc:** `docs/learned/planning/terminology-standards.md`

This maintains the abstraction that allows plans to work with different backends (GitHub issues, draft PRs, future providers).

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Empty Commit via Plumbing Pattern

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** `commit_files_to_branch(files={})` is the non-obvious equivalent to `git commit --allow-empty`. May warrant tripwire if empty commits become a common pattern.

### 2. Graphite Requires Checkout (Hybrid Pattern)

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Graphite's `gt submit` requires the branch to be checked out because it operates on "the current stack". This is a Graphite limitation, not an erk design choice. Worth promoting if Graphite integration expands.

### 3. Write Tool for 10+ Scattered Changes

**Score:** 2/10 (Repeated pattern +1, Non-obvious +1)
**Notes:** Prevents formatting issues from sequential Edits. Borderline for tripwire - more of a best practice than a critical warning.

### 4. Inline Imports in Test Files

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Anti-pattern being phased out. Not promoted to tripwire because it's a declining issue, not a recurring trap.
