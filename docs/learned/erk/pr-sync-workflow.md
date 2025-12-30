---
title: erk pr sync Workflow
read_when:
  - "synchronizing a PR with Graphite"
  - "after erk pr checkout"
  - "enabling gt commands on external PR"
---

# erk pr sync Workflow

Registers a checked-out PR branch with Graphite for stack management.

## When to Use

Use `erk pr sync` after checking out a PR that was created elsewhere:

- After `erk pr checkout <pr-number>`
- When a PR was created from GitHub Actions
- When you need to use `gt` commands on an existing PR

## The 8-Step Flow

1. **Validate preconditions** - gh/gt auth, on branch, PR exists and is OPEN
2. **Check Graphite tracking** - Skip if already tracked (idempotent)
3. **Get PR base branch** - From GitHub API
4. **Track with Graphite** - `gt track --parent <base>`
5. **Squash commits** - `gt squash --no-edit`
6. **Update commit message** - From PR title/body
7. **Restack** - `gt restack --no-interactive`
8. **Submit with force** - Required because squashing rewrites history

## Example

```bash
# Checkout and sync a PR
erk pr checkout 1973
erk pr sync --dangerous

# Now use Graphite commands
gt pr
gt land
```

> Note: The `--dangerous` flag acknowledges that sync invokes Claude with `--dangerously-skip-permissions`.

## Limitations

- Cannot sync fork PRs (Graphite can't track cross-repo branches)
- PR must be OPEN (not merged/closed)
