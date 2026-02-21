---
title: Impl-Context Staging Directory
read_when:
  - "working with .erk/impl-context/ files"
  - "debugging plan content missing from a draft-PR implementation"
  - "reviewing a PR that contains .erk/impl-context/ files"
  - "understanding how draft-PR plans transfer content to .impl/"
tripwires:
  - action: "reviewing a PR that contains .erk/impl-context/ files"
    warning: "Leave a PR comment telling the author to remove .erk/impl-context/. This is an erk tooling error — the directory should have been cleaned up before implementation. Run: git rm -rf .erk/impl-context/ && git commit -m 'Remove leaked impl-context'"
  - action: "removing git-tracked temporary directories in setup scripts"
    warning: "Defer deletion to the git cleanup phase (git rm + commit + push), not shutil.rmtree(). setup_impl_from_issue.py reads the files but deliberately does NOT delete them — see the comment at line 202. Deletion is handled by plan-implement.md Step 2d."
    score: 8
  - action: "adding a new setup path to plan-implement without routing through Step 2d"
    warning: "Impl-context cleanup routing: all code paths that set up an implementation context must route through Step 2d in plan-implement.md, which is the single convergence point for .erk/impl-context/ cleanup. Adding a new setup path that bypasses Step 2d will silently skip cleanup, leaving .erk/impl-context/ files in the final PR diff."
    score: 9
  - action: "calling `create_worker_impl_folder()` without checking `worker_impl_folder_exists()` first"
    warning: "Both submit paths use LBYL: `if worker_impl_folder_exists(): remove_worker_impl_folder()` before creating. Stale .worker-impl/ from a prior failed submission causes errors."
---

# Impl-Context Staging Directory

`.erk/impl-context/` is a temporary staging directory used during draft-PR plan saving. It exists on the plan branch between plan creation and the start of implementation, then gets cleaned up.

## Lifecycle

### Creation

During `plan_save.py`, after creating the plan branch, the script:

1. Checks out the plan branch
2. Creates `.erk/impl-context/` and writes `plan.md` (plan content) and `ref.json` (plan reference metadata)
3. Stages and commits both files
4. Pushes to remote
5. Checks out the original branch

This commit gives the draft PR a non-empty diff (GitHub rejects PRs with no file changes) and enables inline plan review via the "Files Changed" tab.

See: `src/erk/cli/commands/exec/scripts/plan_save.py:163-182`

### Cleanup

The directory is cleaned up before implementation begins via a two-phase deferred cleanup pattern. All five setup paths converge at **Step 2d** in `plan-implement.md`, which is the single cleanup point:

1. **`setup_impl_from_issue.py`** (Phase 1, read-only) — Reads `plan.md` and `ref.json`, copies content into `.impl/`, but deliberately does NOT delete the directory. See comment at `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:202`: "Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push"

2. **`plan-implement.md` Step 2d** (Phase 2, git cleanup — convergence point) — All five setup paths (ISSUE_ARG, FILE_ARG, existing `.impl/` with issue tracking, existing `.impl/` without issue tracking, fallback plan-save) reach this step. Performs the actual deletion with `git rm -rf .erk/impl-context/ && git commit && git push`. This deferred approach ensures removal is committed, not just deleted from the local filesystem. The step is **idempotent** — safe to run even when the directory doesn't exist.

3. **`plan-implement.yml` CI workflow** — Cleans up before the implementation agent runs, as a safety net for remote execution.

### Why It Could Leak (Historical)

Prior to PR #7747 (#7752), cleanup was not guaranteed across all setup paths — if a path bypassed Step 2d, the files would persist on the branch and appear in the final PR diff. This has been fixed: all paths now converge at Step 2d.

The key failure mode was confusing "delete from disk" (shutil.rmtree) with "remove from git tracking" (git rm + commit + push). When adding a new setup path, always route through the Step 2d convergence point — skipping it silently bypasses cleanup.

## Prevention Strategies

### Worker-Impl Cleanup

Both submit paths use the LBYL pattern to clean up stale `.worker-impl/` before creating a new one:

<!-- Source: src/erk/cli/commands/submit.py, worker_impl_folder_exists -->

See the `worker_impl_folder_exists()` / `remove_worker_impl_folder()` LBYL guard in `src/erk/cli/commands/submit.py`. Both submit paths use this pattern to prevent errors from a prior failed submission leaving a stale `.worker-impl/` directory behind (fixed in PR #7687).

### Deferred Impl-Context Deletion

`setup_impl_from_issue.py:202` reads the impl-context files but deliberately does NOT delete them. The comment is explicit:

> "Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push"

This deferred pattern exists because filesystem deletion (`shutil.rmtree`) only removes the local copy. The files remain in git tracking and appear in the PR diff. Only `git rm` + commit + push removes them from the branch history.

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend that uses impl-context
- [Draft PR Lifecycle](draft-pr-lifecycle.md) — Full lifecycle of draft-PR plans
- [Draft PR Branch Sync](draft-pr-branch-sync.md) — Branch sync before implementation
