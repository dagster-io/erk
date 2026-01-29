---
title: Complete File Inventory Protocol
read_when:
  - "estimating effort for a plan or PR"
  - "auditing what changed in a PR before review"
  - "creating a consolidation plan from multiple PRs"
---

# Complete File Inventory Protocol

Before estimating effort for a plan or PR, always run a complete file inventory. Incomplete inventories lead to underestimated effort and silent omissions.

## The Problem

Plans that skip file inventory systematically undercount work:

- Files added by the PR but not mentioned in the plan
- Configuration changes (settings.json, pyproject.toml) that accompany code changes
- Test files that need updating alongside source changes
- Documentation files that need creation or updates

## Inventory Checklist

Before estimating effort, verify:

1. **Files changed**: `gh pr view --json files` or `git diff --name-only`
2. **Files added**: New files introduced by the work
3. **Files deleted**: Files removed as part of cleanup
4. **Configuration changes**: Settings, CI workflows, project config
5. **Generated files**: Index files, tripwires files that need regeneration

## When to Run Inventory

- Before creating a consolidation plan from multiple PRs
- Before estimating remaining work on a partially-complete plan
- Before closing a plan issue as "complete" — verify all items were addressed

## Pattern

```bash
# For a PR
gh pr view <number> --json files --jq '.files[].path'

# For uncommitted work
git diff --name-only

# For a branch vs trunk
git diff --name-only main...HEAD
```

Compare the inventory against the plan's items to identify gaps.
