# Restrict CI to impl-stage PRs only

## Context

Plan PRs (stages: prompted, planning, planned) are created as GitHub draft PRs. The `ci.yml` workflow has draft detection on `pull_request` events, but its `push` trigger fires for ALL branches with no draft check (push events lack `github.event.pull_request` context). This means any push to a plan branch triggers full CI unnecessarily.

## Change

**File: `.github/workflows/ci.yml` (lines 3-6)**

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

No other files need changes. `code-reviews.yml` already uses `pull_request` trigger only.

## Verification

1. Confirm the trigger section change in `ci.yml`
2. Run `erk exec yaml-lint` or similar if available, otherwise visual inspection of YAML indentation
