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

The directory is cleaned up before implementation begins via a two-phase deferred cleanup pattern. Three cleanup paths exist:

1. **`setup_impl_from_issue.py`** (Phase 1, read-only) — Reads `plan.md` and `ref.json`, copies content into `.impl/`, but deliberately does NOT delete the directory. See comment at `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:202`: "Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push"

2. **`plan-implement.md` Step 2d** (Phase 2, git cleanup) — Performs the actual deletion with `git rm -rf .erk/impl-context/ && git commit && git push`. This deferred approach ensures removal is committed, not just deleted from the local filesystem.

3. **`plan-implement.yml` CI workflow** — Cleans up before the implementation agent runs, as a safety net for remote execution.

### Why It Can Leak

If Phase 2 is skipped — for example, `plan-implement.md` Step 2d is not executed, or only the local filesystem was cleaned without a git commit — the files persist on the branch and appear in the final PR diff. The key failure mode is confusing "delete from disk" (shutil.rmtree) with "remove from git tracking" (git rm + commit + push).

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend that uses impl-context
- [Draft PR Lifecycle](draft-pr-lifecycle.md) — Full lifecycle of draft-PR plans
- [Draft PR Branch Sync](draft-pr-branch-sync.md) — Branch sync before implementation
