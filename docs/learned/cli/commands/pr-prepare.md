---
title: erk pr prepare Command
read_when:
  - "setting up impl-context for an existing PR"
  - "preparing a worktree for plan implementation"
  - "working with erk pr prepare"
---

# erk pr prepare Command

Sets up `.erk/impl-context/` for the current worktree's PR, making it ready for plan implementation without full checkout.

## Usage

```bash
erk pr prepare              # Auto-detect PR from current branch
erk pr prepare <number>     # Prepare for specific plan number
```

## Implementation

**File:** `src/erk/cli/commands/pr/prepare_cmd.py`

### Auto-Detection

When `number` is omitted, uses `ctx.github.get_pr_for_branch()` to find the PR associated with the current branch.

### Idempotency

Before creating impl-context, reads any existing impl directory and compares the plan ID. If the plan ID matches, skips setup — safe to re-run.

### Core Logic

Delegates to `create_impl_context_from_pr()` in `setup_impl_from_pr.py` which handles fetching the plan content and creating the impl directory structure.

## Context

The `erk pr prepare` command was introduced alongside the Graphite divergence fix. After checkout, Graphite retracking was moved to AFTER rebase in `checkout_cmd.py` to prevent cached SHA mismatches.

The `erk pr checkout` error message now suggests `erk pr prepare` as an alternative when checkout fails.

## Related Documentation

- [Impl-Context Staging Directory](../../planning/impl-context.md) — impl-context file structure
- [erk pr diverge-fix Command](pr-diverge-fix.md) — branch divergence resolution
