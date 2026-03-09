# Plan: Consolidated Documentation from 23 erk-learn Plans

> **Consolidates:** #9054, #9052, #9051, #9050, #9045, #9042, #9040, #9038, #9037, #9034, #9032, #9028, #9026, #9018, #9017, #9015, #9010, #9008, #9002, #9001, #8998, #8996, #8834

## Context

23 erk-learn plans accumulated over Mar 6-9, 2026. Deep investigation of all plans reveals that most source PRs are fully implemented and many are already well-documented. This consolidated plan focuses only on the **remaining documentation gaps** — new docs to create and existing docs to update.

## Source Plans

| # | Title | Items Merged |
|---|-------|-------------|
| #9054 | Add remote repo support to objective plan with --repo flag | 2 items |
| #9052 | Add objective link insertion to PR body | 1 item |
| #9038 | Unify launch dispatch via RemoteGitHub single code path | 3 items |
| #9037 | Convert erk launch to @no_repo_required with --repo flag | 2 items |
| #9028 | Fix: update_local_ref desyncs checked-out worktrees | 3 items |
| #9026 | Add CI job to block .erk/impl-context/ from merging | 1 item |
| #9045 | Implement autonomous consolidate-learn-plans workflow | 1 item |
| #9008 | Fix changelog-commits JSON output size | 1 item |
| #9010 | Improve Graphite rebase handling skip tracking check | 1 item |

**13 plans with NO remaining gaps** (fully documented, close with no action):
#9051, #9050, #9042, #9040, #9034, #9032, #9017, #9015, #9001, #9002, #8998, #8996, #8834

**1 plan with incomplete code** (defer documentation):
#9018 — `is_rebasing` field never implemented; trunk branch work overlaps with #9017 (already documented)

## Investigation Findings

### Corrections to Original Plans

- **#8834**: Referenced `discover-reviews` as "tier 3 job" but it's in `code-reviews.yml` (pull_request-only), not ci.yml — no skip condition needed
- **#9018**: `is_rebasing` field on `WorktreeInfo` was never implemented — code is incomplete, skip documentation
- **#8998**: Original plan said "5-space indentation" but implementation correctly uses 4-space

### Overlap Analysis

- **#9054, #9038, #9037**: All use `resolve_owner_repo()`, `repo_option`, `resolved_repo_option` — merge into single repo-resolution doc
- **#9038, #9037**: Both cover ref resolution patterns — merge into single ref-resolution doc
- **#9054, #9037**: Both need remote testing patterns — merge into single testing doc
- **#9002, #8998**: Both fix `land_learn.py` formatting — already documented in `land-learn-integration.md`
- **#9040, #8834**: Both modify `fix-formatting` behavior — already documented in `job-ordering-strategy.md`

## Remaining Gaps

### New Documents to Create (7)

1. **Repo resolution pattern** — covers resolve_owner_repo, repo_option, resolved_repo_option
2. **Unified dispatch pattern** — RemoteGitHub-based handlers, post-dispatch enrichment
3. **sync_branch_to_sha pattern** — git reset --hard atomicity for checked-out branches
4. **CI merge gate jobs** — no-impl-context job pattern
5. **Ref resolution patterns** — --ref-current guard, default branch fallback
6. **Remote paths testing** — NoRepoSentinel + FakeRemoteGitHub test patterns
7. **Consolidate-learn-plans workflow** — new workflow, skills, dispatch pattern

### Existing Documents to Update (4)

8. **git-plumbing-patterns.md** — add sync_branch_to_sha reference
9. **incremental-dispatch.md** — update from update_local_ref to sync_branch_to_sha
10. **remote-github-gateway.md** — add RemotePRInfo/RemotePRNotFound types
11. **rebase-confirmation-workflow.md** — add tracking check bypass detail

## Implementation Steps

### Step 1: Create `docs/learned/cli/repo-resolution-pattern.md` _(from #9054, #9038, #9037)_

**Content outline:**
1. Problem: Commands need optional `--repo owner/name` for remote operation
2. `resolve_owner_repo()` function at `src/erk/cli/repo_resolution.py:18-49` — validates format, falls back to local repo
3. `@repo_option` decorator — adds `--repo` Click option
4. `@resolved_repo_option` decorator at `repo_resolution.py:87-103` — wraps resolve_owner_repo for cleaner signatures
5. `get_remote_github()` factory at `repo_resolution.py:52-75` — creates RemoteGitHub with test injection
6. Usage examples from `plan_cmd.py:584` and `launch_cmd.py`

**Verification:** All symbols exist in `src/erk/cli/repo_resolution.py`

### Step 2: Create `docs/learned/architecture/unified-dispatch-pattern.md` _(from #9038)_

**Content outline:**
1. Problem: Dual local/remote code paths in launch_cmd.py (917 lines)
2. Solution: Single RemoteGitHub-based handler pattern (467 lines)
3. Handler signature: `(ctx, owner, repo_name, ...)` — local inferred via resolve_owner_repo
4. Return convention: `(branch_name, run_id)` tuples for post-dispatch enrichment
5. Post-dispatch: `maybe_update_plan_dispatch_metadata()` pattern
6. All 5 unified handlers in `launch_cmd.py`

**Source:** `src/erk/cli/commands/launch_cmd.py` (467 lines, 5 handlers)

**Verification:** No `_launch_local` or `_launch_remote` functions exist

### Step 3: Create `docs/learned/architecture/sync-branch-to-sha-pattern.md` _(from #9028)_

**Content outline:**
1. Problem: `update_local_ref` desyncs checked-out worktrees (ref updated but index/working tree stale)
2. Solution: `sync_branch_to_sha()` at `dispatch_helpers.py:12-40` — uses `git reset --hard` for atomicity
3. Dirty worktree rejection: checks uncommitted changes before reset
4. Call sites: dispatch_cmd.py, incremental_dispatch.py, branch/checkout_cmd.py, pr/checkout_cmd.py
5. When to use vs `ensure_trunk_synced`

**Source:** `src/erk/cli/commands/pr/dispatch_helpers.py:12-40`

**Verification:** All 4 call sites import `sync_branch_to_sha`

### Step 4: Create `docs/learned/ci/merge-gate-jobs.md` _(from #9026)_

**Content outline:**
1. Pattern: Independent CI jobs that block merging bad content
2. `no-impl-context` job at `.github/workflows/ci.yml:30-42`
3. Runs independently (no job dependencies)
4. Skip conditions: draft PRs, erk-plan-review labeled PRs
5. Error message includes remediation steps
6. Note: Branch protection not currently enabled — job runs but isn't required

**Source:** `.github/workflows/ci.yml:30-42`

**Verification:** Job exists and runs independently

### Step 5: Create `docs/learned/cli/ref-resolution-patterns.md` _(from #9037, #9054)_

**Content outline:**
1. `--ref-current` guard: prevents use in remote mode (no local branches to reference)
2. Default branch fallback: `remote.get_default_branch_name()` when no ref specified
3. Local config precedence: `ctx.config.dispatch_ref` > current branch > default branch
4. Implementation in `launch_cmd.py` ref resolution logic

**Source:** `src/erk/cli/commands/launch_cmd.py` ref resolution blocks

**Verification:** `--ref-current` guard exists in launch_cmd.py

### Step 6: Create `docs/learned/testing/remote-paths-testing.md` _(from #9054, #9037)_

**Content outline:**
1. Pattern: Testing commands with `--repo` flag
2. Context setup: `context_for_test(repo=NoRepoSentinel(), remote_github=FakeRemoteGitHub(...))`
3. FakeRemoteGitHub configuration for test scenarios
4. Reference implementations: `test_launch_remote_paths.py`, `test_plan_remote_paths.py`

**Source:** `tests/commands/launch/test_launch_remote_paths.py`, `tests/commands/objective/test_plan_remote_paths.py`

**Verification:** Both test files exist and use the pattern

### Step 7: Create `docs/learned/planning/consolidate-learn-plans-workflow.md` _(from #9045)_

**Content outline:**
1. Two skills: `/erk:consolidate-learn-plans` (interactive), `/erk:consolidate-learn-plans-plan` (CI)
2. Workflow: `.github/workflows/consolidate-learn-plans.yml` — multi-job pipeline
3. Dispatch module: `consolidate_learn_plans_dispatch.py` — branch naming convention
4. Launch integration: `launch_cmd.py:257-266` handler
5. Constants: `CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME` in constants.py

**Source:** Multiple files across `.claude/commands/`, `.github/workflows/`, `src/erk/cli/commands/`

**Verification:** All files exist per investigation

### Step 8: Update `docs/learned/architecture/git-plumbing-patterns.md` _(from #9028)_

**Changes:**
- Lines 85-104: Update checked-out branch section to reference `sync_branch_to_sha`
- Add cross-reference to new `sync-branch-to-sha-pattern.md`
- Note that `update_local_ref` is still used for non-checked-out branches

**Verification:** Updated section accurately reflects `dispatch_helpers.py`

### Step 9: Update `docs/learned/planning/incremental-dispatch.md` _(from #9028)_

**Changes:**
- Line 46 area: Update to mention `sync_branch_to_sha` for branch synchronization
- Add note about dispatch metadata update (from #9050)

**Verification:** Cross-reference with `incremental_dispatch.py`

### Step 10: Update `docs/learned/architecture/remote-github-gateway.md` _(from #9037)_

**Changes:**
- Add section for `get_pr()` method types: `RemotePRInfo` and `RemotePRNotFound`
- Document fields: number, title, state, url, head_ref_name, base_ref_name, owner, repo, labels
- State mapping: API open/closed/merged -> OPEN/CLOSED/MERGED

**Source:** `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`

**Verification:** Types exist in types.py

### Step 11: Update `docs/learned/cli/rebase-confirmation-workflow.md` _(from #9010)_

**Changes:**
- Line 32 area: Expand the in-progress path to explain WHY tracking check is bypassed
- Add note: "When rebase is in progress, tracking validation is skipped because the branch may be in a detached HEAD state"

**Source:** `src/erk/cli/commands/pr/rebase_cmd.py:94-126`

**Verification:** Conditional logic at line 97 skips tracking when `is_rebase_in_progress()`

## Attribution

Items by source:
- **#9054**: Steps 1, 5, 6
- **#9052**: (PR body link pattern — medium priority, covered by existing objective-summary-format.md)
- **#9038**: Steps 1, 2, 5
- **#9037**: Steps 1, 5, 6, 10
- **#9028**: Steps 3, 8, 9
- **#9026**: Step 4
- **#9045**: Step 7
- **#9008**: (JSON truncation — minor, covered by commit-categorizer.md agent doc)
- **#9010**: Step 11

## Verification

After implementation:
1. Run `erk docs sync` to regenerate index
2. Verify all new docs appear in `docs/learned/index.md`
3. Grep for broken cross-references: `grep -r "sync-branch-to-sha" docs/learned/`
4. Confirm tripwires updated where relevant
