# Plan: Restrict CI to impl-stage PRs only

## Context

Plan PRs (stages: prompted, planning, planned) are created as **GitHub draft PRs**. The `ci.yml` workflow has draft detection on `pull_request` events, but its `push` trigger fires for ALL branches with no draft check (push events lack `github.event.pull_request` context). This means any push to a plan branch that includes non-`.erk/impl-context/` files triggers full CI unnecessarily.

The fix: restrict the `push` trigger to `master` only. CI for PRs flows entirely through `pull_request` events, which properly respect draft status.

## Change

**File: `.github/workflows/ci.yml`** (lines 3-6)

Replace:
```yaml
on:
  push:
    paths-ignore:
      - '.erk/impl-context/**'
```

With:
```yaml
on:
  push:
    branches: [master]
```

No other files need changes. `code-reviews.yml` already only uses `pull_request` trigger. All other workflows are manual (`workflow_dispatch`/`workflow_call`).

## How CI flows after this change

| Event | When | CI runs? |
|---|---|---|
| Plan saved (draft PR created) | `pull_request: opened` | No - draft check skips all jobs |
| Push during implementation | `pull_request: synchronize` | No - still a draft |
| `gh pr ready` after impl | `pull_request: ready_for_review` | **Yes** |
| Empty commit trigger (plan-implement.yml line 447) | `pull_request: synchronize` | **Yes** (PR is non-draft after `gh pr ready`) |
| Merge to master | `push` to master | **Yes** |

## Verification

1. Confirm the change in ci.yml triggers section
2. Verify `code-reviews.yml` needs no change (already `pull_request` only)
3. Confirm plan-implement.yml's "Trigger CI workflows" empty commit (line 447) still works via `pull_request: synchronize` after `gh pr ready` (line 395)
