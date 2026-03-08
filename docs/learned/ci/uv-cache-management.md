---
title: UV Cache Management in CI
read_when:
  - "debugging slow CI jobs or GitHub Actions cache issues"
  - "modifying setup-uv configuration"
  - "CI jobs timing out in post-job cleanup"
tripwires:
  - action: "CI job timing out in post-job cleanup"
    warning: "check if UV cache pruning is enabled. Use prune-cache: false for ephemeral CI runners."
---

# UV Cache Management in CI

## Problem

The `astral-sh/setup-uv@v7` GitHub Action runs post-job cache pruning by default. This pruning step can take ~5 minutes, significantly slowing CI jobs.

## Solution

Disable cache pruning in the setup-uv action configuration:

```yaml
- uses: astral-sh/setup-uv@v7
  with:
    prune-cache: false
```

## Rationale

Ephemeral CI runners (GitHub Actions) don't benefit from cache pruning:

- The runner is destroyed after each job
- Pruning only saves cache space for future restores
- The time cost (~5 min) exceeds any space savings

## Location

See the `setup-uv` step in `.github/actions/erk-remote-setup/action.yml`.
