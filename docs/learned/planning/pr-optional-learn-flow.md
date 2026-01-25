---
title: PR Optional Learn Flow
read_when:
  - "understanding when learn step is required vs optional"
  - "landing PRs from remote vs local worktrees"
  - "configuring prompt_learn_on_land"
  - "skipping learn check for specific PR types"
---

# PR Optional Learn Flow

The learn step in the PR landing workflow is conditionally triggered based on whether sessions exist to learn from.

## When Learn is Required

Learn check runs during the **validation phase** (before any mutations) when:

1. **Plan branch** - Branch follows `P{issue_number}-*` pattern
2. **Local context** - Either:
   - Currently on the branch (`is_current_branch=True`), OR
   - Branch has an associated worktree (`worktree_path is not None`)

```python
# From land_cmd.py
plan_issue_number = extract_leading_issue_number(target.branch)
if plan_issue_number is not None and (
    target.is_current_branch or target.worktree_path is not None
):
    _check_learn_status_and_prompt(...)
```

## When Learn is Optional (Skipped)

### Remote-Only PRs

When landing a PR that has no local worktree:

```python
# Both conditions false → skip learn check
target.is_current_branch = False   # Not on this branch
target.worktree_path = None        # No local worktree
```

**Rationale**: No local Claude sessions exist for remote-only PRs. Sessions are stored in worktree-specific paths, so without a local worktree, there's nothing to learn from.

### Learn Plan Issues

Issues labeled `erk-learn` are skipped:

- These are plans for extracting insights, not "being learned from"
- Prevents circular learn-from-learn scenarios

### Config Override

Users can disable the prompt globally or per-repo:

```toml
# ~/.erk/config.toml (global)
prompt_learn_on_land = false

# .erk/config.toml (repo-level)
prompt_learn_on_land = false

# .erk/config.local.toml (local override)
prompt_learn_on_land = false
```

### Force Flag

The `--force` flag skips all interactive prompts including learn:

```bash
erk land --force
```

## Validation Phase Placement

The learn check occurs during validation (before execution) for safety:

```
┌─────────────────────────────────────┐
│          VALIDATION PHASE           │
├─────────────────────────────────────┤
│ 1. Resolve target (PR/branch/current)│
│ 2. Check PR is mergeable            │
│ 3. Check local changes              │
│ 4. Check conflicts                  │
│ 5. Check learn status ← HERE        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│          EXECUTION PHASE            │
├─────────────────────────────────────┤
│ 1. Merge PR                         │
│ 2. Delete branch                    │
│ 3. Clean up worktree                │
│ 4. Update objective (if linked)     │
└─────────────────────────────────────┘
```

This ensures the user is prompted about learn **before** any mutations occur.

## Decision Tree

```
Is this a plan branch (P{issue}-*)?
├── No → Skip learn check
└── Yes → Is there local context?
    ├── is_current_branch=True → Run learn check
    ├── worktree_path is not None → Run learn check
    └── Both False → Skip learn check (remote-only)
```

## Test Reference

See `tests/commands/land/test_learn_skip_remote.py`:

- `test_land_skips_learn_prompt_for_remote_pr()` - Verifies skip with no local worktree
- `test_land_shows_learn_prompt_for_local_plan_branch()` - Verifies check runs with local worktree

## Related Topics

- [Config Override Chains](../architecture/config-override-chains.md) - Config precedence
- [Learn Workflow](learn-workflow.md) - Full learn workflow documentation
- [Plan Lifecycle](lifecycle.md) - Plan states and transitions
