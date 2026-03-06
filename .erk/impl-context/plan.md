# Fix: Automated pushes attributed to user instead of bot

## Context

Automated CI workflows (plan-implement, pr-address, etc.) push commits that GitHub attributes to the user who dispatched the plan. This happens because:

1. **Checkout uses `ERK_QUEUE_GH_PAT`** (a personal access token) — GitHub attributes push events to the token owner
2. **`git config user.name "$SUBMITTED_BY"`** — commits are authored as the submitter

The user wants pushes to show as `github-actions[bot]`, not as themselves.

## Root Cause

`actions/checkout` with a PAT configures the git credential helper for ALL subsequent `git push` commands in that job. GitHub attributes the push event to the PAT owner regardless of `git config user.name`.

## Approach

Switch `actions/checkout` to use `github.token` in all workflows. This makes pushes show as `github-actions[bot]`. Handle the one case that requires PAT (CI trigger) differently.

**Key constraint:** Pushes with `github.token` do NOT trigger workflow events (GitHub security feature). The "Trigger CI workflows" step in plan-implement.yml relies on this. Fix by using `gh workflow run` with the PAT instead of empty-commit-push.

## Changes

### 1. plan-implement.yml

**Checkout (line 114):** `token: ${{ secrets.ERK_QUEUE_GH_PAT }}` -> `token: ${{ github.token }}`

**Remove `$SUBMITTED_BY` git config overrides** (lines 163-164, 215-216, 369-370, 409-410, 444-445): Replace with `github-actions[bot]` identity:
```yaml
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
```

**Push session (line 273):** Keep `GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}` — push-session uses git plumbing with its own auth, not the checkout credential. Test if `github.token` works here; if so, switch it too.

**Update plan header (line 289):** `ERK_QUEUE_GH_PAT` -> `github.token` (pure API call)

**Trigger CI workflows (lines 438-450):** Replace empty-commit-push with explicit workflow dispatch:
```yaml
- name: Trigger CI workflows
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
  run: |
    # Use PAT for workflow dispatch (push with github.token won't trigger CI)
    gh workflow run ci.yml --ref "$BRANCH_NAME"
    echo "CI workflows triggered via workflow dispatch"
```
Note: ci.yml must already support `workflow_dispatch` trigger. Verify this.

### 2. pr-address.yml

- **Checkout (line 41):** Switch to `github.token`
- **Pure API steps (lines 54, 155):** Switch to `github.token`
- **Push session (line 139):** Test with `github.token`, keep PAT if needed

### 3. pr-rewrite.yml

- **Checkout (line 49):** Switch to `github.token`
- **Pure API steps (lines 62, 104, 140):** Switch to `github.token`

### 4. pr-rebase.yml

- **Checkout (line 54):** Switch to `github.token`
- **Pure API steps (lines 67, 165):** Switch to `github.token`

### 5. one-shot.yml

- **Checkout (line 88):** Switch to `github.token`
- **Pure API steps (lines 128, 186, 194, 210):** Switch to `github.token`
- **Plan execution (line 154):** Audit what ops this drives; switch if no user-scoped calls

### 6. learn.yml

- **Checkout (line 52):** Switch to `github.token`
- **Pure API steps (line 65):** Switch to `github.token`

### 7. ci.yml (line 66) — DO NOT CHANGE

The auto-fix formatting checkout MUST use PAT because it pushes fixes that need to re-trigger CI. This is the correct use of PAT and is not an attribution problem (it's the CI bot fixing formatting, user doesn't interact with it).

### 8. Update documentation

**docs/learned/ci/github-token-scopes.md:**
- Fix contradictory entries (line 42 says push fails with `github.token`, line 65 says it works)
- Update the "Checkout with PAT" row — PAT checkout is now only needed for ci.yml auto-fix
- Document the `gh workflow run` pattern for CI triggering

## Files to modify

- `.github/workflows/plan-implement.yml`
- `.github/workflows/pr-address.yml`
- `.github/workflows/pr-rewrite.yml`
- `.github/workflows/pr-rebase.yml`
- `.github/workflows/one-shot.yml`
- `.github/workflows/learn.yml`
- `docs/learned/ci/github-token-scopes.md`

## NOT changing

- `.github/workflows/ci.yml` — PAT required for auto-fix re-trigger
- `.github/actions/erk-remote-setup/action.yml` — still receives PAT for non-push uses

## Verification

1. Dispatch a plan-implement run and verify GitHub shows `github-actions[bot]` for push events
2. Verify CI triggers successfully after implementation (the `gh workflow run` replacement)
3. Verify push-session still works (may need PAT)
4. Verify all pure API operations (plan header updates, comments) still succeed
