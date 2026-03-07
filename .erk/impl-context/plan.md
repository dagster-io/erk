# Plan: Disable uv cache pruning in erk-remote-setup

## Context

The `implement` job in `plan-implement.yml` failed because `astral-sh/setup-uv@v7`'s automatic post-job cache pruning timed out after ~5 minutes and exited with code 2. This is a post-cleanup step managed by the action itself — all actual work had completed successfully. The cache pruning failure caused the entire job to be marked as failed, which is misleading.

The regular CI setup action (`setup-python-uv`) doesn't hit this because it has a smaller cache footprint. The remote implementation jobs run longer and accumulate more cached packages, making pruning expensive.

## Change

**File:** `.github/actions/erk-remote-setup/action.yml` (line 30)

Add `prune-cache: false` to the `setup-uv` step:

```yaml
- uses: astral-sh/setup-uv@v7
  with:
    prune-cache: false
```

This disables the post-job cache pruning that's timing out. The cache will still be saved/restored — it just won't be pruned, which is fine for CI runners with ephemeral storage.

## Verification

- Check that the `plan-implement.yml` workflow no longer fails due to uv cache pruning
- Confirm uv still installs packages correctly (cache save/restore still works)
