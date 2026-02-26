# Documentation Plan: Update tests to exercise branch-scoped impl-context primary code paths

## Context

This plan synthesizes learnings from PR #8335, which completed Phase 2 of the `.impl/` to `.erk/impl-context/<branch>/` migration. The PR updated ~290 test references across 18 files to exercise the new branch-scoped primary code paths instead of relying on legacy fallback behavior. This was a mechanical but critical migration enabling parallel implementation workflows.

The sessions associated with this PR demonstrate several cross-cutting patterns: error recovery from Graphite state confusion, frozen context path handling after directory mutations, multi-node objective planning, and efficient PR review workflows with batch thread resolution. These patterns benefit future agents working on test infrastructure, worktree operations, and CLI commands.

Documentation matters here because the migration establishes new standard patterns for test setup (`get_impl_dir()` with `BRANCH` constant) that all future test development should follow. Additionally, several failure modes discovered during implementation (Graphite submit failures, frozen context CWD issues) warrant tripwires to prevent other agents from hitting the same problems.

## Raw Materials

PR #8335

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 15    |
| Contradictions to resolve      | 2 (both are stale file paths) |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score2-3) | 6     |

## Documentation Items

### HIGH Priority

#### 1. Fix phantom file paths in impl-context.md

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Source:** [Impl]

**Phantom References:**
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (MISSING - should be `setup_impl.py` or `setup_impl_from_pr.py`)
- `src/erk/cli/commands/submit.py` (MISSING - should be `src/erk/cli/commands/pr/submit_cmd.py`)

**Cleanup Instructions:**
Replace phantom paths with actual current file paths at lines 43, 48, and 68. The document describes correct concepts; only the file references are outdated due to refactoring. Verify the functionality descriptions still match the current code after updating paths.

---

#### 2. Fix phantom file path in issue-pr-linkage-storage.md

**Location:** `docs/learned/erk/issue-pr-linkage-storage.md`
**Action:** INVESTIGATE then UPDATE_REFERENCES or DELETE_SECTION
**Source:** [Impl]

**Phantom References:**
- `src/erk/cli/commands/exec/scripts/get_closing_text.py` (MISSING at lines 45, 144)

**Cleanup Instructions:**
Investigate where the `get_closing_text` functionality moved. If moved to another file, update references. If functionality was removed entirely, delete the section describing it. Document was last audited 2026-02-17 (14% phantom rate).

---

#### 3. Branch-scoped impl directory architecture

**Location:** `docs/learned/architecture/branch-scoped-impl-dirs.md`
**Action:** CREATE
**Source:** [PR #8335]

**Draft Content:**

```markdown
# Branch-Scoped Implementation Directories

## Overview

Erk uses branch-scoped implementation directories to enable parallel implementations across multiple branches. The structure `.erk/impl-context/<branch>/` replaces the legacy flat `.impl/` directory.

## Why Branch-Scoped?

1. **Parallel implementations**: Multiple branches can have separate impl directories without conflicts
2. **Visibility clarity**: `.erk/impl-context/` is committed to git (visible in PRs); `.impl/` is never committed (local working directory)
3. **Organization**: Branch-scoped directories prevent state leakage between implementations

## Core API

### `get_impl_dir(base_path, branch_name)`

Pure path computation for branch-scoped impl directories. See `packages/erk-shared/src/erk_shared/impl_folder.py` for implementation.

- Input: Base path (repo root) and branch name
- Output: Path to `.erk/impl-context/<sanitized-branch>/`
- Branch names with slashes are sanitized: `feature/test` becomes `feature--test`

### `resolve_impl_dir(repo_root, branch_name)`

Discovery function with fallback chain:
1. Try branch-scoped: `.erk/impl-context/<branch>/` (primary)
2. Try legacy: `.impl/` (backward-compatible fallback)
3. Try discovery: Scan `.erk/impl-context/` for any subdir with `plan.md`
4. Return None if nothing found

## Migration Timeline

- **Phase 1**: Production code migration (PRs #8215, #8279, #8302, #8314)
- **Phase 2**: Test suite migration (PR #8325)
- **Phase 3**: CI workflow updates and legacy removal (PRs #8326+)

## Usage Pattern

See `tests/core/test_impl_folder.py` for canonical examples of both primary and legacy fallback testing.
```

---

#### 4. Test patterns for branch-scoped impl directories

**Location:** `docs/learned/testing/impl-context-test-patterns.md`
**Action:** CREATE
**Source:** [PR #8335]

**Draft Content:**

```markdown
# Impl-Context Test Patterns

Standard patterns for tests that interact with implementation directories.

## Pattern A: Branch-Scoped Directory Creation

Use `get_impl_dir()` for all new tests:

```python
from erk_shared.impl_folder import get_impl_dir

BRANCH = "feature/test-branch"
"""Test branch name used across tests."""

def test_something(tmp_path: Path) -> None:
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)  # parents=True required for nested path
```

**Key points:**
- Import `get_impl_dir` from `erk_shared.impl_folder`
- Define `BRANCH` constant at module level for consistency
- Always use `parents=True` with `mkdir()` (branch-scoped paths are nested)

## Pattern B: Ref File Usage

Use `ref.json` (not `plan-ref.json`) for new tests:

```python
(impl_dir / "ref.json").write_text(json.dumps(ref_data))
```

## Legacy Fallback Tests

Tests that explicitly verify backward compatibility with `.impl/` should keep using the legacy path. See `test_resolve_impl_dir_legacy_fallback()` in `tests/core/test_impl_folder.py`.

## Parameter Naming

When test functions accept a path parameter representing the repository root, name it `repo_root` for semantic clarity:

```python
def _setup_plan_ref(repo_root: Path, *, plan_id: str) -> None:
    impl_dir = get_impl_dir(repo_root, branch_name=BRANCH)
```
```

---

### MEDIUM Priority

#### 5. Fail-open operations pattern

**Location:** `docs/learned/cli/fail-open-operations.md`
**Action:** CREATE
**Source:** [Plan] from session dd0f4f19

**Draft Content:**

```markdown
# Fail-Open Operations

When secondary operations run after primary mutations have succeeded, they must be fail-open to avoid negating the primary success.

## Pattern

1. Primary operation succeeds (e.g., PR merge via `erk land`)
2. Secondary operation runs (e.g., objective update)
3. Secondary operation catches ALL exceptions
4. Log warnings but always exit 0
5. Document the fail-open contract in function docstrings

## Rationale

The primary operation has already succeeded and been pushed to GitHub. Secondary operations (like objective tracking updates) are best-effort. Failures in secondary operations must not cause the overall command to error or appear to fail.

## Implementation

See `run_objective_update_after_land()` in `src/erk/cli/commands/objective_helpers.py` for the canonical example. The function:
- Runs after PR has been merged and worktree deleted
- Catches all exceptions
- Logs warnings but never raises
- Has explicit fail-open contract in docstring

## Related Patterns

The `impl-signal` exec scripts (`started`, `ended`, `submitted`) use `|| true` pattern for graceful failures when plan reference is unavailable.
```

---

#### 6. Multi-node objective planning

**Location:** `docs/learned/objectives/multi-node-planning.md`
**Action:** CREATE
**Source:** [Plan] from session 03394738

**Draft Content:**

```markdown
# Multi-Node Objective Planning

When a user requests planning multiple related objective nodes together, agents can combine them into a single plan.

## Pattern

1. **Assess relationship**: Are nodes closely related (same phase, same category)?
2. **Create combined marker**: Use `X.Y+X.Z` format for roadmap-step marker
3. **Write single plan**: Plan covers both nodes as cohesive unit
4. **Update both nodes**: After plan-save, run `update-objective-node` for each node

## Example

User: "Plan nodes 4.3 and 4.4"

If both nodes are Phase 4 documentation tasks:
- Create marker: `4.3+4.4`
- Write plan addressing both nodes
- After save: Update node 4.3 to `in_progress` with PR, then node 4.4

## When to Combine vs Separate

**Combine when:**
- Nodes are in same phase
- Nodes address same feature/area
- Work is interdependent

**Separate when:**
- Nodes are unrelated features
- Different teams/reviewers expected
- Work can be done independently
```

---

#### 7. PR review batch resolution workflow

**Location:** `docs/learned/pr-operations/batch-review-workflow.md`
**Action:** CREATE
**Source:** [Impl] from session de99f9b1

**Draft Content:**

```markdown
# PR Review Batch Resolution Workflow

Efficient workflow for addressing multiple PR review comments.

## Two-Phase Approach

1. **Preview**: `/erk:pr-preview-address` - Read-only preview of actionable items
2. **Execute**: `/erk:pr-address` - Full execution with batching

## Batch Classification

Comments are classified by complexity:
- **Local**: Simple fixes that auto-proceed without user confirmation
- **Cross-cutting**: Complex changes requiring user approval

## Batch Thread Resolution

When addressing multiple threads in a single commit, use batch resolution:

```bash
echo '[{"thread_id": "...", "comment": "..."}, ...]' | erk exec resolve-review-threads
```

This is more efficient and atomic than individual `resolve-review-thread` calls.

## Workflow Sequence

1. Preview comments with classifier
2. Read file context around flagged lines
3. Make code fixes
4. Run tests via devrun subagent
5. Commit with batch message
6. Resolve all threads in single batch call
7. Update PR description with `erk exec update-pr-description`
8. Submit via `/local:quick-submit`
```

---

#### 8. Bot review false positive detection

**Location:** `docs/learned/review/bot-review-false-positives.md`
**Action:** CREATE
**Source:** [Impl] from session de99f9b1 + PRCommentAnalyzer

**Draft Content:**

```markdown
# Bot Review False Positive Detection

Automated review bots can misdiagnose issues. Agents should verify code behavior before applying suggestions.

## Decision Framework

When automated review bot flags code:

1. **Read flagged code carefully** before making changes
2. **Verify the pattern** - Is it actually incorrect?
3. **Check context** - Did bot misunderstand the surrounding code?
4. **For false positives**: Reply explaining why, resolve thread without code changes

## Example: Dead Code vs Variable Inlining

Bot flagged: "Variable `_branch` is declared but only used once immediately after"

Reality discovered: `_branch` was assigned but NEVER used (next line used different value directly). This was dead code removal, not variable inlining.

**Learning**: Bot misdiagnosed dead code as variable inlining. Always verify actual usage patterns.

## When to Challenge

- Bot suggestion doesn't match actual code behavior
- Surrounding context provides justification bot missed
- Applying suggestion would introduce bugs

## When to Apply

- Bot correctly identified issue
- Fix improves code quality
- Change aligns with project conventions
```

---

#### 9. Expand Context Regeneration section with frozen CWD failure modes

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [Plan] from session dd0f4f19

**Draft Content Additions:**

Add subsection to "Context Regeneration" section:

```markdown
### Frozen CWD and Directory Mutations

`ErkContext.cwd` is set at construction time and never updates. When operations delete directories (e.g., worktree cleanup in `erk land`), the frozen `ctx.cwd` becomes invalid.

**Pattern**: Compute and cache valid paths (like main repo root) before mutations, then pass them explicitly to post-mutation operations.

**Example**: `run_objective_update_after_land()` in `objective_helpers.py` accepts an explicit `worktree_path` parameter instead of relying on `ctx.cwd`, because the worktree may be deleted before the function runs.

**Prevention**: Before passing `ctx.cwd` to external processes after worktree operations, check if the directory may have been deleted. Compute and cache valid paths before operations that might delete directories.
```

---

#### 10. Parameter naming for semantic clarity

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl] from session de99f9b1 + PRCommentAnalyzer

**Draft Content Addition:**

Add to naming conventions section:

```markdown
### Parameter Naming: Semantic Meaning Over Source

Parameter names should reflect their semantic meaning (what the value represents) rather than their source (where the value comes from).

**Example**: Test function receiving a path from pytest's `tmp_path` fixture:

```python
# Before: Named after source (pytest fixture)
def _setup_plan_ref(tmp_path: Path, *, plan_id: str) -> None:
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)

# After: Named for semantic role (repository root)
def _setup_plan_ref(repo_root: Path, *, plan_id: str) -> None:
    impl_dir = get_impl_dir(repo_root, branch_name=BRANCH)
```

The parameter is used as a repository root, so naming it `repo_root` documents the contract more clearly than `tmp_path` which only indicates where the value originates.
```

---

#### 11. Variable scoping clarity pattern

**Location:** `docs/learned/patterns/variable-scoping.md`
**Action:** CREATE
**Source:** [Impl] from session de99f9b1

**Draft Content:**

```markdown
# Variable Scoping for Clarity

Guidelines for when to inline single-use values vs create intermediate variables.

## When to Inline

Inline single-use values when:
- Value is used immediately on the next line
- No intermediate computation or transformation
- Inlining doesn't exceed reasonable line length
- Name would just repeat the value (e.g., `branch_name = "main"` followed by `get_impl_dir(..., branch_name=branch_name)`)

## When to Extract

Extract to variable when:
- Value is used multiple times
- Name documents intent (not obvious from value)
- Line length becomes unwieldy
- Debugging benefits from named intermediate

## Example from PR #8335

```python
# Before: Unnecessary intermediate variable
_branch = "plnd/add-feature-01-04-1234"
impl_dir = get_impl_dir(env.cwd, branch_name=_branch)

# After: Inlined for clarity
impl_dir = get_impl_dir(env.cwd, branch_name="plnd/add-feature-01-04-1234")
```

The variable `_branch` added no documentation value (the literal string is self-documenting) and was only used once immediately after assignment.
```

---

#### 12. Bot review feedback loop workflow

**Location:** `docs/learned/ci/bot-review-workflow.md`
**Action:** CREATE
**Source:** [Impl] from session de99f9b1

**Draft Content:**

```markdown
# Bot Review Feedback Loop Workflow

How to work with automated review bots during the PR lifecycle.

## The Loop

1. **Submit PR** - Bot automatically reviews
2. **Receive comments** - Bot flags potential issues
3. **Preview feedback** - `/erk:pr-preview-address` shows actionable items
4. **Address feedback** - `/erk:pr-address` processes comments
5. **Bot re-reviews** - After push, bot evaluates changes
6. **Iterate** - Repeat until bot approves or issues are resolved

## Activity Logs

Bot comments include activity logs tracking resolution:
- When thread was created
- When agent addressed it
- Whether fix was accepted

## Best Practices

1. **Batch changes**: Address multiple comments in one commit when related
2. **Verify before fixing**: Don't blindly apply bot suggestions
3. **Document disagreements**: When not applying a suggestion, explain why in thread reply
4. **Re-check after push**: Verify bot accepted the changes
```

---

### LOW Priority

#### 13. Dead code detection heuristics

**Location:** `docs/learned/refactoring/dead-code-detection.md`
**Action:** CREATE
**Source:** [Impl] from session de99f9b1

**Draft Content:**

```markdown
# Dead Code Detection Heuristics

Patterns that indicate dead code during refactoring.

## Variable Redeclaration Pattern

When a variable is declared but then the same name is assigned a different value before use, the first declaration is dead code.

**Example from PR #8335:**

```python
_branch = "plnd/add-feature-01-04-1234"  # Assigned
impl_dir = env.cwd / ".impl"  # _branch never used, impl_dir computed differently
```

The `_branch` variable was assigned but never referenced before going out of scope.

## Other Signals

- Variable assigned inside conditional but never used outside
- Import statement for symbol never referenced
- Function defined but never called
- Parameter accepted but never used in function body
```

---

#### 14. Main repo root discovery via common dir

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [Plan] from session dd0f4f19

**Draft Content Addition:**

Add subsection:

```markdown
### Lightweight Main Repo Discovery

When you need the main repo root from a worktree context but don't need full `RepoContext`, use the common dir pattern:

```python
common_dir = git.repo.get_git_common_dir()
main_repo_root = common_dir.parent
```

This works for both:
- Worktrees: common dir points to main repo's `.git`
- Regular repos: common dir is the `.git` directory

This is lighter weight than `discover_repo_context()` which requires global config access and validation.

See `packages/erk-shared/src/erk_shared/git_gateway.py` for the `get_git_common_dir()` implementation.
```

---

#### 15. Direct GitHub CLI as erk fallback

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] from session 69698be2

**Draft Content Addition:**

Add tripwire entry:

```markdown
- **Trigger**: `erk pr submit` or similar erk commands fail unexpectedly
- **Warning**: When erk commands fail due to internal state issues (e.g., Graphite confusion), direct `gh` commands provide an escape hatch. Verify the actual state with `gh pr diff <number>`, then use `gh pr edit` + `gh pr ready` to complete the operation manually.
- **Score**: 3
```

---

## Contradiction Resolutions

### 1. Phantom File Paths in impl-context.md

**Existing doc:** `docs/learned/planning/impl-context.md` (lines 43, 48, 68)

**Conflict:** References non-existent files:
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (MISSING)
- `src/erk/cli/commands/submit.py` (MISSING)

**Actual Files:**
- `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py`
- `src/erk/cli/commands/exec/scripts/setup_impl.py`
- `src/erk/cli/commands/pr/submit_cmd.py`

**Resolution:** Update file paths to match current codebase. The concepts described are correct; only the source file references need correction.

---

### 2. Phantom File Path in issue-pr-linkage-storage.md

**Existing doc:** `docs/learned/erk/issue-pr-linkage-storage.md` (lines 45, 144)

**Conflict:** References `src/erk/cli/commands/exec/scripts/get_closing_text.py` (MISSING)

**Resolution:** Investigate where the functionality moved. If moved, update reference. If removed, delete the section. Document was audited recently (2026-02-17) so this is likely a minor path change.

---

## Stale Documentation Cleanup

### 1. impl-context.md phantom paths

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`, `submit.py` (2 phantoms, 33% phantom rate)
**Cleanup Instructions:** Replace with actual file paths. Verify functionality descriptions match current code.

---

### 2. issue-pr-linkage-storage.md phantom path

**Location:** `docs/learned/erk/issue-pr-linkage-storage.md`
**Action:** INVESTIGATE then UPDATE_REFERENCES or DELETE_SECTION
**Phantom References:** `get_closing_text.py` (1 phantom, 14% phantom rate)
**Cleanup Instructions:** Find where functionality moved, or remove section if functionality was deleted.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Graphite State Confusion During PR Submit

**What happened:** `erk pr submit` failed with "This branch does not introduce any changes" despite 1266 lines changed on GitHub.

**Root cause:** Graphite's `gt submit` returned empty diff due to internal state confusion with sibling branches in the stack.

**Prevention:** Before running `erk pr submit`, verify branch state with `gt info --no-interactive`. Check for sibling branches in complex stacks. Have fallback workflow ready: verify actual diff with `gh pr diff <number>`, then use `gh pr edit` + `gh pr ready` to complete submission manually.

**Recommendation:** TRIPWIRE

---

### 2. Frozen Context CWD After Directory Mutations

**What happened:** After `erk land` merged PR and deleted worktree, the objective update failed because Claude CLI couldn't start in the deleted worktree directory.

**Root cause:** `ErkContext.cwd` is frozen at construction time. After worktree deletion, `ctx.cwd` points to a non-existent path, but is still passed to external processes.

**Prevention:** Compute and cache valid directory paths before operations that might delete directories. Pass explicit `worktree_path` parameters instead of relying on frozen `ctx.cwd`.

**Recommendation:** TRIPWIRE

---

### 3. Git Branch Name Assumptions

**What happened:** `git log --oneline main..HEAD` failed with exit code 128.

**Root cause:** Repository uses `origin/main` (remote tracking branch), not a local `main` branch.

**Prevention:** Use `origin/main` or `origin/master` with fallback pattern. Never assume local `main` branch exists. Check with `git remote show origin` or `git branch -r` first.

**Recommendation:** TRIPWIRE

---

### 4. Plan Nodes Already Complete

**What happened:** Agent started implementing plan nodes but discovered source changes were already merged in prior PRs.

**Root cause:** Plan created before PRs merged, not updated to reflect current master state.

**Prevention:** Always verify plan nodes against current codebase with grep before implementation. Check if source files mentioned in plan are already modified.

**Recommendation:** ADD_TO_DOC (planning docs)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Graphite State Confusion During erk pr submit

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Running `erk pr submit` and getting "This branch does not introduce any changes" error despite actual diff on GitHub.

**Warning:** Verify actual diff exists with `gh pr diff <number> | wc -l`. If non-zero, bypass with `gh pr edit` + `gh pr ready` workflow. Graphite state can become confused with sibling branches in stack.

**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/cli/tripwires.md`

This tripwire is critical because the failure is silent (appears to succeed from erk's perspective but PR never gets submitted) and affects all PR submissions when Graphite state becomes corrupted. The workaround is non-obvious.

---

### 2. Frozen Context CWD After Directory Mutations

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** Passing `ctx.cwd` to external processes after worktree cleanup or other directory-deleting operations.

**Warning:** Compute and cache valid directory paths before operations that might delete directories. Pass explicit `worktree_path` parameters instead of relying on frozen `ctx.cwd`. See: `run_objective_update_after_land()` in objective_helpers.py.

**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire prevents a class of bugs where operations succeed (merge, delete) but follow-up actions fail because they use stale path references from the frozen context.

---

### 3. Git Branch Name Assumptions

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** Using git log with hardcoded branch names like `main..HEAD` or assuming `main` branch exists locally.

**Warning:** Use `origin/main` or `origin/master` with fallback pattern. Never assume local `main` branch exists. Check `git remote show origin` or `git branch -r` first.

**Target doc:** `docs/learned/architecture/tripwires.md`

Many repositories don't have a local `main` branch, only remote tracking branches. Git commands assuming local `main` will fail silently or with confusing errors.

---

### 4. Auto-Generated Tripwire File Edits

**Score:** 4/10 (Non-obvious +2, Silent failure +2)

**Trigger:** Editing files with `<!-- AUTO-GENERATED FILE -->` headers directly.

**Warning:** Check file header for auto-generation comment. If present, update source frontmatter in original docs, then run `erk docs sync` to regenerate. Never edit index files directly - changes will be lost on next sync.

**Target doc:** `docs/learned/documentation/tripwires.md`

Auto-generated files like tripwire index files get overwritten by `erk docs sync`. Direct edits appear to work but are silently lost.

---

### 5. Documenting Deprecated-but-Supported Files

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** Writing documentation about file references that have legacy alternatives still supported in code.

**Warning:** Describe current primary file first, note legacy fallback as "(or legacy X)" in validation/error contexts. Don't remove legacy references if code still supports them as fallback. Example: `plan-ref.json` (primary) vs `issue.json` (legacy fallback).

**Target doc:** `docs/learned/documentation/tripwires.md`

Removing legacy file references from docs when code still supports them causes confusion when users encounter legacy files in existing implementations.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Direct GitHub CLI as erk Fallback

**Score:** 3/10 (External tool quirk +1, Cross-cutting +2)

**Notes:** Useful workaround but not critical - no data loss risk. When erk commands fail, `gh` commands provide escape hatch. Could be promoted to tripwire if this becomes a frequent issue.

---

### 2. impl-signal Graceful Failures

**Score:** 3/10 (Non-obvious +2, Silent failure +1)

**Notes:** The `|| true` pattern for non-critical exec scripts is by design, not an error condition. Commands fail gracefully when plan-ref.json is missing. Documented but not tripwire-worthy since it's expected behavior.

---

### 3. Multi-Node Objective Planning

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Workflow adaptation for combining related nodes. Not an error prevention pattern - more of a workflow optimization. Good for documentation but not tripwire-worthy.

---

### 4. Legacy Fallback Test Preservation

**Score:** 2/10 (Non-obvious +2)

**Notes:** When migrating tests to new patterns, some tests should be preserved to verify backward compatibility. Testing pattern, not production code concern.

---

### 5. False Positive Bot Reviews

**Score:** 2/10 (Non-obvious +2)

**Notes:** Code quality issue about verifying bot suggestions before applying. Not blocking or destructive - just causes unnecessary code churn.

---

### 6. Parameter Naming Semantic Clarity

**Score:** 2/10 (Non-obvious +2)

**Notes:** Code quality pattern about naming parameters for meaning vs source. Good practice but low severity if not followed.
