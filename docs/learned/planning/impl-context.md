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
---

# Impl-Context Staging Directory

`.erk/impl-context/` is a temporary staging directory used during draft-PR plan saving. It exists on the plan branch between plan creation and the start of implementation, then gets cleaned up.

## What It Contains

- **`plan.md`** — The plan content (identical to what appears in the PR body's `<details>` block)
- **`ref.json`** — Plan reference metadata (`provider`, `title`, and optionally `objective_id`)

## Lifecycle

### Creation

During `plan_save.py`, after creating the plan branch, the script:

1. Checks out the plan branch
2. Creates `.erk/impl-context/` and writes `plan.md` + `ref.json`
3. Stages and commits both files
4. Pushes to remote
5. Checks out the original branch

This commit gives the draft PR a non-empty diff (GitHub rejects PRs with no file changes) and enables inline plan review via the "Files Changed" tab.

See: `src/erk/cli/commands/exec/scripts/plan_save.py:163-182`

### Cleanup

The directory is removed before implementation begins. Three cleanup paths exist:

1. **`setup_impl_from_issue.py`** (primary) — Reads `plan.md` and `ref.json`, copies content into `.impl/`, then calls `shutil.rmtree()` on the directory. See: `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:186-204`

2. **`plan-implement.md` Step 2d** (manual fallback) — If `.erk/impl-context/` still exists in git tracking after setup, removes it with `git rm -rf` and commits.

3. **`plan-implement.yml` CI workflow** — Cleans up before the implementation agent runs, as a safety net for remote execution.

### Why It Can Leak

If any cleanup path fails silently — for example, `setup_impl_from_issue` removes the local directory but doesn't commit the removal, or the CI cleanup step is skipped — the files persist on the branch and appear in the final PR diff.

## The Constant

The directory path is defined as `IMPL_CONTEXT_DIR` in `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:86`:

```python
IMPL_CONTEXT_DIR = ".erk/impl-context"
```

All code references this constant rather than hardcoding the path.

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend that uses impl-context
- [Draft PR Lifecycle](draft-pr-lifecycle.md) — Full lifecycle of draft-PR plans
- [Draft PR Branch Sync](draft-pr-branch-sync.md) — Branch sync before implementation
