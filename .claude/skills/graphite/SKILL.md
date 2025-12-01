---
name: Graphite Stack Management
description: Guide for using Graphite (gt) CLI for stacked pull requests. Use when working with gt commands, stacked PRs, stack navigation, or when users mention graphite, gt, upstack, downstack, restack, or stack-based workflows.
allowed-tools: Read, Grep, Glob, Bash
---

# Graphite Stack Management

## When to Use This Skill

Activate this skill when:

- User mentions "gt", "graphite", "stack", or "stacked PRs"
- Working with stack navigation (upstack/downstack)
- Creating or managing dependent branches
- Questions about gt commands or workflows
- Integrating gt with workstack worktrees

## Core Mental Model

**Graphite enables stacked pull requests**: breaking large features into small, dependent, reviewable changes.

Key concepts:

- **Stack**: Linear chain of dependent branches (main → feat-1 → feat-2 → feat-3)
- **Parent/Child**: Each branch (except trunk) has exactly one parent
- **Auto-restacking**: Changes to a branch automatically propagate upstack
- **Directional navigation**: "down" toward trunk, "up" away from trunk

## Essential Commands Quick Reference

### Creating & Modifying

```bash
gt create [name]           # Create new branch on current + commit
gt modify                  # Amend current + restack children
gt submit --stack          # Push + create/update all PRs
```

### Navigation

```bash
gt up / gt down            # Move through stack
gt top / gt bottom         # Jump to ends
gt log                     # Visualize stack
```

### Maintenance

```bash
gt sync                    # Update from remote + cleanup merged
gt restack                 # Rebase stack to include parent changes
```

## Common Workflows

### 1. Creating a Stack

```bash
gt checkout main
gt create phase-1 -m "Add API endpoints"
# ... make changes, stage with git add ...
gt modify -m "Update API endpoints"

gt create phase-2 -m "Update frontend"
# ... make changes, stage ...
gt modify -m "Update frontend"

gt submit --stack          # Submit all PRs
```

### 2. Responding to Review Feedback

```bash
# Navigate to branch needing changes
gt down                    # Move toward trunk
gt down                    # Continue until at target

# Make changes
git add .
gt modify -m "Address review feedback"
# Automatically restacks all upstack branches!

gt submit --stack          # Update all affected PRs
```

### 3. After PRs Merge

```bash
gt sync                    # Fetches, rebases, prompts to delete merged
```

## Workstack Integration

Graphite metadata is stored in `.git/` and shared across all worktrees:

- `.git/.graphite_cache_persist`: Branch relationships (parent/child graph)
- `.git/.graphite_pr_info`: Cached GitHub PR information
- `.git/.graphite_repo_config`: Repository config (trunk branch)

**Workstack commands that use gt**:

- `workstack list --stacks`: Shows stack relationships
- `workstack tree`: Visualizes stacks
- Code: `src/workstack/core/graphite_ops.py`

## Important Rules

1. **Use gt commands, not raw git**: `gt modify` instead of `git commit --amend`
2. **Delete with gt**: `gt delete` instead of `git branch -d` (updates metadata)
3. **gt submit includes downstack**: Use `--stack` flag to include upstack too
4. **Run gt sync after merges**: Keeps stack clean and up-to-date

## Detailed Documentation

For comprehensive documentation including:

- Complete command reference with all options
- Metadata file formats and structures
- Advanced workflow patterns
- Practical examples with conflict resolution
- AI agent integration guidance

See: `.agent/packages/tools/gt/gt.md`

## Quick Troubleshooting

| Issue                                     | Solution                                            |
| ----------------------------------------- | --------------------------------------------------- |
| "Branch needs restacking"                 | Run `gt restack`                                    |
| Merge conflicts during sync               | Resolve conflicts, run `gt continue`                |
| Multiple children, unsure which to follow | `gt up` prompts to select; `gt log` shows structure |
| Stack visualization looks wrong           | Run `gt sync` to refresh from GitHub                |

## Command Aliases

```bash
gt c   = gt create
gt m   = gt modify
gt s   = gt submit
gt ss  = gt submit --stack
gt u   = gt up
gt d   = gt down
gt t   = gt top
gt b   = gt bottom
gt l   = gt log
gt co  = gt checkout
gt r   = gt restack
```

## Example: Reading Stack Information Programmatically

```python
from pathlib import Path
import json

def load_graphite_metadata(git_dir: Path) -> dict:
    """Load gt branch relationships from .graphite_cache_persist."""
    cache_file = git_dir / ".graphite_cache_persist"
    if not cache_file.exists():
        return {}

    data = json.loads(cache_file.read_text(encoding="utf-8"))
    branches = {}
    for branch_name, metadata in data.get("branches", []):
        branches[branch_name] = metadata
    return branches
```

## Integration with Workstack Worktrees

When using gt with workstack:

1. All worktrees share the same gt metadata (stored in common `.git/`)
2. `gt log` shows all stacks across all worktrees
3. Can work on separate stacks in parallel worktrees
4. Use `workstack list --stacks` to see which worktree is on which stack

Example workflow:

```bash
# In main worktree: work on auth stack
gt create auth-model
gt create auth-service

# Create separate worktree for different feature
workstack create billing-feature
workstack switch billing-feature

# In billing worktree: work on billing stack
gt create billing-model
gt create billing-service

# gt log shows BOTH stacks from any worktree
```
