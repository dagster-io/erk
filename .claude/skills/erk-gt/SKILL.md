---
name: erk-gt
description:
  Erk-specific Graphite (gt) patterns. Supplements the official `graphite` skill
  with agent safety rules, metadata internals, worktree integration, and debugging.
  Load the `graphite` skill first for base gt knowledge.
---

# Erk Graphite Patterns

This skill supplements the official `graphite` skill with erk-specific patterns. Load `graphite` first for base command reference and workflows.

## CRITICAL: Always Use `--no-interactive`

**NEVER invoke any `gt` command without `--no-interactive`.** This is a global flag inherited by every gt command — not a per-command option.

Without `--no-interactive`, gt may open prompts, pagers, or editors that hang indefinitely in agent/CI contexts. The `--force` flag does NOT prevent prompts — you must use `--no-interactive` separately.

```bash
# WRONG - may hang waiting for user input
gt sync
gt submit --force
gt track --parent main

# CORRECT - always pass --no-interactive
gt sync --no-interactive
gt submit --no-interactive
gt track --parent main --no-interactive
gt restack --no-interactive
gt create my-branch -m "message" --no-interactive
```

**What `--interactive` controls (all disabled by `--no-interactive`):**

- Prompts (confirmation dialogs in sync, delete, submit, etc.)
- Pagers (output paging in log)
- Editors (commit message editing in create/modify, PR metadata in submit)
- Interactive selectors (branch selection in checkout, move, track)

**Note:** `gt modify --interactive-rebase` is a separate, unrelated flag that starts a git interactive rebase. It is NOT the same as the global `--interactive`.

## Programmatic Parent Resolution

Use `gt parent` or `gt branch info` — never parse `gt log short` output.

```bash
# Get parent branch name
parent=$(gt parent --no-interactive)

# Or from gt branch info (more context: parent, children, commit, PR)
parent=$(gt branch info --no-interactive | grep "Parent:" | awk '{print $2}')

# Use for diff operations
git diff "$parent...HEAD"
```

**Anti-patterns:**

- ❌ Parsing `gt log short` tree visualization (counterintuitive format, confuses agents)
- ❌ Using `git merge-base` when Graphite is available
- ❌ Guessing parent branches from branch names

## Metadata Storage

All gt metadata lives in the shared `.git` directory (accessible across worktrees):

| File                           | Purpose                                        |
| ------------------------------ | ---------------------------------------------- |
| `.git/.graphite_repo_config`   | Trunk branch config                            |
| `.git/.graphite_cache_persist` | Branch parent-child graph (the core DAG)       |
| `.git/.graphite_pr_info`       | Cached GitHub PR state, review decisions, URLs |

### Branch Graph (`.graphite_cache_persist`)

Array of `[branchName, metadata]` tuples:

```json
{
  "branches": [
    ["main", { "validationResult": "TRUNK", "children": ["feat-1"] }],
    [
      "feat-1",
      {
        "parentBranchName": "main",
        "children": ["feat-2"],
        "branchRevision": "abc123...",
        "validationResult": "VALID"
      }
    ]
  ]
}
```

Key fields: `parentBranchName`, `children`, `branchRevision`, `validationResult` (VALID, TRUNK, BAD_PARENT_NAME).

### Worktree Sharing

**All worktrees see the same gt metadata** because it's in the common `.git` directory:

```bash
# Same result from any worktree
git rev-parse --git-common-dir  # → /path/to/repo/.git/
```

This is how erk reads stack information from any worktree without needing gt installed in each one.

## Erk Integration

Erk reads gt metadata directly for stack visualization and PR status:

- **`erk list --stacks`**: Reads `.graphite_cache_persist` to show stack relationships
- **`erk sync`**: Delegates to `gt sync` subprocess
- **PR info**: Reads `.graphite_pr_info` for PR state without GitHub API calls

**Graceful degradation**: If gt is not installed (`use_graphite = false` in `~/.erk/config.toml`), erk works without stack info. Cache files missing → functions return None.

**Source files**: `src/erk/cli/graphite.py`, `src/erk/core/graphite_ops.py`

## Debugging

### Quick Diagnostics

```bash
gt ls --no-interactive                    # Branch in stack?
gt branch info <branch> --no-interactive  # Parent, children, PR
cat .git/.graphite_cache_persist | jq '.branches[] | select(.[0]=="<branch>")'
```

### Recovery from Corrupted State

```bash
# Nuclear option: re-initialize (loses stack relationships)
rm .git/.graphite_cache_persist
gt repo init --no-interactive

# Re-track branches manually
gt track --branch feature-1 --parent main --no-interactive
gt track --branch feature-2 --parent feature-1 --no-interactive
```
