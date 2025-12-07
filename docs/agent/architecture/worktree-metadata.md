---
title: Worktree Metadata Storage
read_when:
  - "storing per-worktree data"
  - "working with worktrees.toml"
  - "associating metadata with worktrees"
---

# Worktree Metadata Storage

## Overview

Per-worktree metadata is stored in `~/.erk/repos/{repo}/worktrees.toml`. This file associates worktree names with metadata like project paths.

## File Location

```
~/.erk/repos/
└── {repo-name}/
    ├── config.toml      ← Repo-level configuration
    └── worktrees.toml   ← Per-worktree metadata
```

## Format

```toml
[feature-x]
project = "python_modules/dagster-open-platform"

[another-wt]
project = "python_modules/another-project"
```

## API

**File**: `src/erk/core/worktree_metadata.py`

```python
# Read project for a worktree
project_path = get_worktree_project(repo_dir, worktree_name, git_ops)

# Set project for a worktree
set_worktree_project(repo_dir, worktree_name, project_path)

# Remove worktree metadata (called when worktree deleted)
remove_worktree_metadata(repo_dir, worktree_name)
```

## Usage

- **`erk wt create`**: Records project association if created from project context
- **`erk wt goto`**: Looks up project path and navigates to project subdirectory
- **`erk wt rm`**: Removes metadata when worktree is deleted

## Subdirectory Navigation Patterns

Some commands support navigating to subdirectories within worktrees rather than just the worktree root. Erk uses two patterns for this:

### Project Path Pattern (wt goto)

The `wt goto` command looks up stored project metadata to navigate to a project subdirectory:

```python
# From wt/goto_cmd.py
project_path = get_worktree_project(repo.repo_dir, worktree_name, ctx.git)
if project_path is not None:
    target_path = worktree_path / project_path
else:
    target_path = worktree_path
```

This pattern is used when worktrees have **permanent project associations** stored in `worktrees.toml`.

### Relative Path Pattern (checkout, up, down)

Navigation commands can preserve the user's **current relative position** by:

1. Computing relative path from current worktree root to cwd
2. Applying that path to target worktree
3. Falling back to worktree root if path doesn't exist

This pattern is useful for commands that switch between worktrees while maintaining the user's position in the directory structure. The activation script in `activation.py` can be extended to support this pattern.

**Comparison**:

| Pattern | Use Case | Storage | Example Commands |
|---------|----------|---------|------------------|
| **Project Path** | Permanent project associations | `worktrees.toml` | `erk wt goto` |
| **Relative Path** | Dynamic position preservation | No storage (computed) | `erk checkout`, `erk up`, `erk down` |

## Related Topics

- [Glossary: Project Context](../glossary.md#project-context) - What project context contains
- [Template Variables](../cli/template-variables.md) - Variables available in project configs
