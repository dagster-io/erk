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

## Related Topics

- [Glossary: Project Context](../glossary.md#project-context) - What project context contains
- [Template Variables](../cli/template-variables.md) - Variables available in project configs
