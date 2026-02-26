# Documentation Plan: Complete Phase 1: Consolidate .impl/ folder discovery into unified pattern

## Context

This plan captures documentation needs from PR #8314, which completed Phase 1 of the `.impl/` folder consolidation effort (Objective #8197, nodes 1.6-1.8). The implementation unified discovery logic across the codebase by making `resolve_impl_dir()` the canonical method for finding implementation folders, eliminating the `impl_type` distinction between "legacy" and "branch-scoped" formats.

The sessions implementing this PR revealed significant pain points around the Graphite + git rebase workflow, where agents spent 60%+ of time resolving branch divergence issues. The discovery that `gt track` must follow `git rebase` to refresh Graphite's commit cache is a high-value tripwire that will prevent substantial debugging time for future agents. Additionally, a format mismatch between `impl_context.py` (flat format) and `impl_folder.py` (branch-scoped) was diagnosed but not fixed in this PR, representing known technical debt.

Documentation is valuable here because: (1) the consolidation introduces breaking changes for external consumers of exec script JSON output, (2) the discovery algorithm's multi-step fallback is used by 15+ files but has zero agent documentation, and (3) the Graphite reconciliation workflow is non-obvious and caused repeated failures until the correct sequence was discovered.

## Raw Materials

PR #8314 implementation sessions and diff analysis

## Summary

| Metric | Count |
| --- | --- |
| Documentation items | 16 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 5 |
| Potential tripwires (score 2-3) | 3 |

## Stale Documentation Cleanup

Existing docs with inaccuracies requiring action before new content:

### 1. setup-impl-from-issue flow inaccuracy

**Location:** `docs/learned/cli/erk-exec-commands.md` (lines 166-167)
**Action:** UPDATE_REFERENCES
**Phantom References:** Documentation describes `create_branch()` + `checkout_branch()` pattern, but actual code uses `_checkout_plan_branch()` for planned-PR plans
**Cleanup Instructions:** Audit the setup-impl-from-issue section and either update to reflect actual code path or remove implementation-level detail that creates drift risk.

### 2. PrCheck named tuple field exposure

**Location:** `docs/learned/cli/erk-exec-commands.md` (line 192)
**Action:** UPDATE_EXISTING
**Issue:** Exposes internal named tuple field names (`PrCheck(passed: bool, description: str)`) creating drift risk
**Cleanup Instructions:** Replace with prose description: "Each check outputs a pass/fail status with a description." This avoids documenting internal implementation details.

## Documentation Items

### HIGH Priority

#### 1. Graphite cache invalidation after git rebase

**Location:** `docs/learned/workflows/tripwires.md` (create) or `docs/learned/erk/tripwires.md` (update)
**Action:** CREATE
**Source:** [Impl] session-1122411e-part2

This was the highest-pain-point discovery across all sessions. Agent spent significant time diagnosing why `gt submit` and `gt restack` failed after `git rebase`.

**Draft Content:**

```markdown
# Workflows Tripwires

<!-- tripwire: graphite-cache-after-rebase, score: 8 -->
## After `git rebase origin/$BRANCH`

**Warning:** Run `gt track --no-interactive` before `gt restack` to refresh Graphite's commit cache.

Git rebase changes commit SHAs outside Graphite's awareness, leaving `.graphite_cache_persist` pointing to stale SHAs. Without the track step, Graphite will report "branch has diverged from Graphite's tracking" and refuse to operate.

**Full reconciliation sequence:**
1. `git fetch origin`
2. Diagnose: `git rev-list --left-right --count HEAD...origin/$BRANCH`
3. `git rebase origin/$BRANCH`
4. `gt track --no-interactive` (refresh cache)
5. `gt restack --no-interactive`
6. `erk pr submit -f` (force push is safe after clean rebase)

See `packages/erk-shared/src/erk_shared/gateway/` for git operations.
```

---

#### 2. resolve_impl_dir() 4-step discovery algorithm

**Location:** `docs/learned/architecture/impl-folder-discovery.md`
**Action:** CREATE
**Source:** [Impl] diff-analysis, session-13ea68ec

Core pattern used by 15+ files but has zero agent documentation. The discovery algorithm is the canonical way to find implementation folders.

**Draft Content:**

```markdown
# Implementation Folder Discovery

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, resolve_impl_dir -->

## Overview

`resolve_impl_dir()` provides unified discovery for implementation folders, supporting both legacy `.impl/` and branch-scoped `.erk/impl-context/<branch>/` formats.

## Discovery Algorithm

The function uses a 4-step fallback:

1. **Branch-scoped**: Check `.erk/impl-context/<sanitized-branch>/plan.md`
2. **Legacy**: Check `.impl/plan.md`
3. **Discovery search**: Scan `.erk/impl-context/` for any subdirectory containing `plan.md`
4. **None**: Return None if no implementation folder found

## Branch Name Sanitization

Branch names are sanitized for directory names using `_sanitize_branch_for_dirname()`:
- `feature/foo` becomes `feature--foo`
- This prevents path separator issues

## Usage

Always use `resolve_impl_dir()` instead of hardcoding `.impl/` paths. The function handles format detection transparently.

See `resolve_impl_dir()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

## Known Limitation

The discovery does not check for flat format at `.erk/impl-context/plan.md` (step 2.5). This affects auto-detection in dispatch workflows. See impl-context-formats.md for details.
```

---

#### 3. Flat vs branch-scoped impl-context format mismatch

**Location:** `docs/learned/planning/impl-context-formats.md`
**Action:** CREATE
**Source:** [Impl] session-13ea68ec

Root cause diagnosis from session: two modules manage `.erk/impl-context/` with incompatible structures.

**Draft Content:**

```markdown
# Implementation Context Formats

## Overview

The codebase has two storage formats for implementation context in `.erk/impl-context/`:

| Format | Structure | Created By | Read By |
|--------|-----------|------------|---------|
| Flat | `.erk/impl-context/plan.md`, `.erk/impl-context/ref.json` | `impl_context.py` (dispatch workflow) | None currently |
| Branch-scoped | `.erk/impl-context/<branch>/plan.md` | `impl_folder.py` (local implementation) | `resolve_impl_dir()` |

## The Problem

`erk pr dispatch` creates flat format files via `create_impl_context()`, but `resolve_impl_dir()` only searches for branch-scoped subdirectories. This causes auto-detection to fail with "No plan numbers provided and could not auto-detect from context" even when `ref.json` with `plan_id` exists.

## Module Ownership

- **`impl_context.py`**: Dispatch workflow, creates committed flat files
- **`impl_folder.py`**: Discovery/resolution, expects branch-scoped subdirectories

## Recommended Fix

Add step 2.5 to `resolve_impl_dir()` to check for flat format at `.erk/impl-context/plan.md` before searching subdirectories.

See `packages/erk-shared/src/erk_shared/impl_folder.py` for discovery logic.
See `packages/erk-shared/src/erk_shared/impl_context.py` for dispatch format creation.
```

---

#### 4. impl_type field removal breaking change

**Location:** `docs/learned/planning/exec-scripts-breaking-changes.md`
**Action:** CREATE
**Source:** [PR #8314] diff-analysis

Breaking change for external consumers parsing exec script JSON output.

**Draft Content:**

```markdown
# Exec Scripts Breaking Changes

## impl_type Field Removal (PR #8314)

**Affected commands:**
- `erk exec impl-init`
- `erk exec setup-impl`

**Change:** The `impl_type` field is no longer included in JSON output.

**Previous output:**
```json
{
  "impl_dir": "/path/to/.impl",
  "impl_type": "legacy",
  "valid": true
}
```

**Current output:**
```json
{
  "impl_dir": "/path/to/.impl",
  "valid": true
}
```

**Migration:** Remove `impl_type` from any parsing logic. The distinction between "legacy" and "branch-scoped" is handled internally by `resolve_impl_dir()`.

**Rationale:** Phase 1 consolidation made the distinction meaningless. All discovery now uses unified `resolve_impl_dir()` which transparently handles both formats.

See `src/erk/cli/commands/exec/scripts/impl_init.py` and `setup_impl.py` for implementation.
```

---

#### 5. setup-impl behavior with missing .impl/ directory

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-1122411e-part1

Non-obvious behavior that required manual workaround during implementation.

**Draft Content:**

```markdown
<!-- tripwire: setup-impl-missing-impl, score: 5 -->
## After successful setup-impl, .impl/plan.md doesn't exist

**Warning:** Fetch plan from GitHub and manually create `.impl/plan.md`.

The `setup-impl` command cleans up `.erk/impl-context/` staging directory after committing, but may not create the `.impl/` directory for the implementation session in all cases.

**Recovery pattern:**
```bash
gh pr view <number> --json body -q .body > /tmp/plan-body.md
# Extract plan content from <details summary="original-plan"> block
mkdir -p .impl
# Write plan.md with extracted content
```

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for setup behavior.
```

---

### MEDIUM Priority

#### 6. Git rebase reconciliation workflow

**Location:** `docs/learned/workflows/reconciliation.md` (create) or `docs/learned/erk/reconciliation.md`
**Action:** CREATE
**Source:** [Impl] session-1122411e-part2

Full sequence documented after multiple failed approaches.

**Draft Content:**

```markdown
# Branch Reconciliation Workflow

## When to Use

When `erk pr submit` reports "branch has diverged from remote" or when git shows commits both ahead and behind.

## Reconciliation Sequence

1. **Fetch remote state:**
   ```bash
   git fetch origin
   ```

2. **Diagnose divergence:**
   ```bash
   git rev-list --left-right --count HEAD...origin/$BRANCH
   ```
   Output: `N    M` means N commits ahead, M commits behind

3. **Rebase onto remote:**
   ```bash
   git rebase origin/$BRANCH
   ```

4. **Refresh Graphite cache:**
   ```bash
   gt track --no-interactive
   ```
   Critical: rebase changes SHAs, Graphite needs cache refresh

5. **Restack if needed:**
   ```bash
   gt restack --no-interactive
   ```

6. **Force submit:**
   ```bash
   erk pr submit -f
   ```
   Force push is safe after clean rebase

## Common Mistakes

- Using `gt get` or `gt sync` when branches have diverged (designed for different scenarios)
- Skipping `gt track` after rebase (causes "diverged from tracking" errors)
- Not using `-f` flag after rebase (divergence check may see stale state)
```

---

#### 7. Force push safety after clean rebase

**Location:** `docs/learned/erk/pr-submission.md` or add to workflows/reconciliation.md
**Action:** UPDATE or CREATE
**Source:** [Impl] session-1122411e-part2

**Draft Content:**

```markdown
## Force Push After Clean Rebase

When `erk pr submit` reports divergence after a clean rebase with no conflicts, use `erk pr submit -f` to force push.

**Why it's safe:** The rebase already incorporated all remote changes. The divergence check compares SHAs before push and may see stale state that doesn't reflect the successful rebase.

**When NOT to use `-f`:**
- Rebase had conflicts that weren't resolved
- You haven't verified remote changes are incorporated
- Working on shared branches where force push affects others
```

---

#### 8. Plan data provider unified discovery

**Location:** `docs/learned/planning/plan-data-provider.md`
**Action:** CREATE
**Source:** [PR #8314] diff-analysis

Documents architectural change in how plan data is discovered.

**Draft Content:**

```markdown
# Plan Data Provider

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, RealPlanDataProvider._build_worktree_mapping -->

## Unified Discovery

The plan data provider uses `resolve_impl_dir()` for discovering implementation folders across all worktrees. This handles both legacy `.impl/` and branch-scoped `.erk/impl-context/<branch>/` transparently.

## Worktree Mapping

`_build_worktree_mapping()` builds a mapping from worktree paths to their implementation folders. For each worktree:

1. Call `resolve_impl_dir(worktree_path)`
2. If result is not None, include in mapping
3. Return complete mapping for downstream consumption

See `RealPlanDataProvider._build_worktree_mapping()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`.
```

---

#### 9. Phase 1 consolidation completion

**Location:** `docs/learned/planning/impl-folder-consolidation.md`
**Action:** CREATE
**Source:** [PR #8314] diff-analysis

Marks major milestone in consolidation effort.

**Draft Content:**

```markdown
# .impl/ Folder Consolidation

## Phase 1 Completion (PR #8314)

Phase 1 of Objective #8197 is complete. Key changes:

### What Changed

1. **Unified discovery**: All code now uses `resolve_impl_dir()` instead of hardcoded `.impl/` paths
2. **Removed impl_type**: The "legacy" vs "branch-scoped" distinction is eliminated
3. **Simplified .gitignore**: Only `.erk/impl-context/` tracked (covers both formats)
4. **Plan data provider**: Uses unified discovery across all worktrees

### Breaking Changes

- `impl_type` field removed from `erk exec impl-init` and `erk exec setup-impl` JSON output
- See exec-scripts-breaking-changes.md for migration

### Remaining Work

Phase 2+ items from Objective #8197:
- Fix flat format detection (step 2.5 in resolve_impl_dir)
- Consider module consolidation (impl_context.py + impl_folder.py)

See Objective #8197 for full roadmap.
```

---

#### 10. Branch-scoped directory pattern

**Location:** `docs/learned/architecture/impl-context-api.md`
**Action:** UPDATE
**Source:** [Impl] session-13ea68ec

**Draft Content:**

Add section to existing doc:

```markdown
## Branch-Scoped Directory Pattern

Implementation folders can be stored under `.erk/impl-context/<branch>/` where `<branch>` is sanitized for filesystem safety.

### Sanitization

`_sanitize_branch_for_dirname()` converts branch names:
- `feature/foo` → `feature--foo`
- `fix/bar-baz` → `fix--bar-baz`

This prevents path separator issues and maintains filesystem compatibility.

See `_sanitize_branch_for_dirname()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.
```

---

#### 11. impl-signal failure handling

**Location:** `docs/learned/planning/impl-context.md` or `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Impl] session-1122411e-part1

**Draft Content:**

Add section:

```markdown
## impl-signal Failure Handling

When `.impl/` is manually created without `plan-ref.json`, `impl-signal` commands will fail with "no-issue-reference". This is expected and harmless.

**Best practice:** Use `|| true` with impl-signal commands in scripts:
```bash
erk exec impl-signal started || true
```

The signal failures are logged with `"success": false` but don't affect implementation workflow.
```

---

#### 12. Module ownership clarification

**Location:** `docs/learned/architecture/impl-context-api.md`
**Action:** UPDATE
**Source:** [Impl] session-13ea68ec

**Draft Content:**

Add to overview section:

```markdown
## Module Responsibilities

| Module | Purpose | Format |
|--------|---------|--------|
| `impl_context.py` | Dispatch workflow (committed files) | Flat: `.erk/impl-context/plan.md` |
| `impl_folder.py` | Discovery and resolution | Branch-scoped: `.erk/impl-context/<branch>/` |

**Note:** These modules manage the same directory with different formats. Format unification is planned for Phase 2+.
```

---

### LOW Priority

#### 13. Prettier formatting on .impl/

**Location:** `docs/learned/ci/tripwires.md` or `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-1122411e-part2

**Draft Content:**

```markdown
<!-- tripwire: prettier-impl-folder, score: 2 -->
## .impl/plan.md fails CI formatting checks

**Warning:** Run `uv run prettier --write .impl/plan.md` before CI.

Prettier checks run on all markdown files including `.impl/` folder. Plan files may not be formatted to Prettier standards initially.
```

---

#### 14. _validate_impl_folder() return type change

**Location:** `docs/learned/planning/tripwires.md` or `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8314] diff-analysis

**Draft Content:**

```markdown
<!-- tripwire: validate-impl-folder-return, score: 2 -->
## _validate_impl_folder() return type changed

**Warning:** Return type changed from `tuple[Path, str]` to `Path`.

Callers unpacking `(impl_dir, impl_type) = _validate_impl_folder(...)` must update to `impl_dir = _validate_impl_folder(...)`.

See `_validate_impl_folder()` in `src/erk/cli/commands/exec/scripts/impl_init.py`.
```

---

#### 15. Fetching plans from draft PRs

**Location:** `docs/learned/planning/plan-retrieval.md`
**Action:** CREATE
**Source:** [Impl] session-1122411e-part1

**Draft Content:**

```markdown
# Plan Retrieval from GitHub

## Recovering Plans from Draft PRs

When `.impl/plan.md` doesn't exist locally, the plan can be recovered from the PR body:

```bash
gh pr view <number> --json body -q .body
```

The plan is stored in a `<details>` block with summary "original-plan" in draft PRs.

**Note:** This pattern may already be documented in planning/planned-pr-backend.md for the `<details>` storage format.
```

---

#### 16. .gitignore consolidation note

**Location:** `docs/learned/planning/workflow.md` or `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #8314] diff-analysis

**Draft Content:**

Add note:

```markdown
## .gitignore Consolidation

As of PR #8314, `.impl/` is no longer in `.gitignore` separately. The directory is covered by `.erk/impl-context/` tracking, which handles both legacy and branch-scoped formats.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Graphite Cache Invalidation After Git Rebase

**What happened:** After running `git rebase origin/$BRANCH`, subsequent `gt submit` and `gt restack` commands failed with "branch has diverged from Graphite's tracking" errors.

**Root cause:** Git rebase changes commit SHAs outside Graphite's awareness. Graphite's internal cache (`.graphite_cache_persist`) continues pointing to old SHAs until explicitly refreshed.

**Prevention:** Always run `gt track --no-interactive` after any raw git operation that changes commit SHAs (rebase, reset, amend).

**Recommendation:** TRIPWIRE - This cost 60%+ of session time and affects any agent doing branch reconciliation.

### 2. setup-impl Missing .impl/ Directory

**What happened:** After successful `setup-impl` command, `.impl/plan.md` didn't exist. Agent had to manually create the directory and populate plan content from GitHub.

**Root cause:** `setup-impl` cleans up `.erk/impl-context/` staging directory after committing, but doesn't guarantee `.impl/` creation in all workflows.

**Prevention:** Document recovery pattern via `gh pr view --json body` for fetching plan content.

**Recommendation:** TRIPWIRE - Non-obvious behavior that requires workaround.

### 3. Flat Format Not in resolve_impl_dir() Search

**What happened:** `erk pr dispatch` failed to auto-detect plan number despite `ref.json` with `plan_id` existing in `.erk/impl-context/`.

**Root cause:** `resolve_impl_dir()` only searches for branch-scoped subdirectories, not flat format at `.erk/impl-context/plan.md`. The dispatch workflow creates flat format via `create_impl_context()`, but discovery doesn't support it.

**Prevention:** Add step 2.5 to `resolve_impl_dir()` to check flat format before subdirectory search.

**Recommendation:** TRIPWIRE + CODE_CHANGE - Affects auto-detection in dispatch workflows.

### 4. Multiple Failed gt get/gt sync Attempts

**What happened:** Agent tried `gt get --no-interactive` and `gt sync` to resolve divergence, but commands didn't fix the underlying issue.

**Root cause:** These commands are designed for different scenarios (new branch vs existing branch). When branch has diverged with both local and remote commits, direct `git rebase` is required.

**Prevention:** Document that diverged branches require `git rebase`, not `gt get/sync`.

**Recommendation:** ADD_TO_DOC - Covered by reconciliation workflow documentation.

### 5. Divergence Check Sees Stale State

**What happened:** `erk pr submit` reported divergence after clean rebase with no conflicts, causing uncertainty about whether to force push.

**Root cause:** Divergence check compares git rev-parse before push and may not reflect successful rebase.

**Prevention:** After clean rebase, use `erk pr submit -f` confidently.

**Recommendation:** ADD_TO_DOC - Clarify when force push is safe.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Graphite cache invalidation after git rebase

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2)
**Trigger:** After running `git rebase` on a branch tracked by Graphite
**Warning:** Run `gt track --no-interactive` before `gt restack` to refresh Graphite's commit cache, otherwise Graphite sees diverged SHAs and refuses to operate.
**Target doc:** `docs/learned/workflows/tripwires.md` or `docs/learned/erk/tripwires.md`

This is the highest-value tripwire from this plan. The session spent over 60% of time debugging this issue. The failure mode is non-obvious (Graphite reports divergence even after successful rebase), cross-cutting (affects any agent doing branch reconciliation), and causes significant time loss when encountered.

### 2. Git rebase reconciliation sequence

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +2, Repeated pattern +1)
**Trigger:** When reconciling branch with remote after divergence
**Warning:** Follow sequence: fetch -> diagnose -> rebase -> track -> restack -> force submit. Do not use `gt get` or `gt sync` when branches have diverged.
**Target doc:** `docs/learned/workflows/tripwires.md` or `docs/learned/erk/tripwires.md`

Complements the Graphite cache tripwire with the full workflow sequence.

### 3. setup-impl missing .impl/ directory

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After successful setup-impl, .impl/plan.md doesn't exist
**Warning:** Fetch plan from GitHub using `gh pr view <number> --json body -q .body` and manually create `.impl/plan.md`. setup-impl cleans `.erk/impl-context/` but may not create `.impl/`.
**Target doc:** `docs/learned/planning/tripwires.md`

Non-obvious behavior that breaks expected workflow.

### 4. Flat format not in resolve_impl_dir() search

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When erk pr dispatch can't auto-detect plan number despite ref.json existing
**Warning:** Check if resolve_impl_dir() includes step 2.5 for flat format. The dispatch workflow creates flat files but discovery only searches branch-scoped subdirectories.
**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/architecture/tripwires.md`

Technical debt that causes auto-detection failures.

### 5. Force push safety after clean rebase

**Score:** 4/10 (Non-obvious +2, External tool quirk +2)
**Trigger:** When erk pr submit reports divergence after clean rebase with no conflicts
**Warning:** Use `erk pr submit -f` to force push. The rebase already incorporated remote changes safely; divergence check may see stale state.
**Target doc:** `docs/learned/erk/tripwires.md`

Clarifies when force push is the correct action.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Format mismatch between impl_context.py and impl_folder.py

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Could be promoted to HIGH if more agents encounter dispatch auto-detection failures. Currently addressed by flat format tripwire above.

### 2. Multiple failed gt get/sync attempts

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Specific to reconciliation workflow; addressed by main reconciliation tripwire. Low independent value.

### 3. impl-signal failures without plan-ref.json

**Score:** 2/10 (Non-obvious +2)
**Notes:** Low severity because failures are expected and harmless. Documentation note is sufficient; full tripwire would add noise.
