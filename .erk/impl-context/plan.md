# Upgrade astral-sh/setup-uv from v5 to v7

## Context

CI run [22748366041](https://github.com/dagster-io/erk/actions/runs/22748366041) failed with `exit code 2` during the `Post Run ./.github/actions/erk-remote-setup` step. The actual implementation succeeded — the failure was in setup-uv's post-job cache pruning. This is a known issue fixed in setup-uv v7.0.0, which uses `uv cache prune --ci --force` to ignore background uv processes that previously blocked pruning.

## Breaking change analysis (v5 → v7)

**v6.0.0 changes — none affect erk:**
- `python-version` no longer auto-activates venv → erk doesn't rely on this (uses `uv sync` or `uv tool install`)
- `pyproject-file`/`uv-file` inputs removed → erk doesn't use these
- Cache dependency glob default changed → no action needed

**v7.0.0 changes — none affect erk:**
- Node 24 instead of Node 20 → GitHub-hosted runners auto-update
- `server-url` input removed → erk doesn't use this
- **Cache pruning fix** → this is the fix we want

## Changes

Replace `astral-sh/setup-uv@v5` with `astral-sh/setup-uv@v7` in all 5 locations:

1. `.github/actions/setup-python-uv/action.yml:13`
2. `.github/actions/erk-remote-setup/action.yml:30`
3. `.github/workflows/ci.yml:304`
4. `.github/workflows/ci.yml:517`
5. `.github/workflows/ci.yml:576`

No input changes needed — all current `with:` blocks are compatible with v7.

## Verification

Push branch, trigger CI, confirm the `Post Run` cleanup step no longer fails with exit code 2.
