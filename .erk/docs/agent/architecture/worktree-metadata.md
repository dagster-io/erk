---
title: Worktree Metadata Storage
read_when:
  - "storing per-worktree data"
  - "working with worktrees.toml"
  - "associating metadata with worktrees"
  - "implementing subdirectory navigation"
  - "preserving relative path on worktree switch"
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

Navigation commands can determine where to navigate within a target worktree. There are two patterns:

### Project Path Pattern (wt goto)

The `wt goto` command uses stored project metadata to navigate to a project subdirectory:

```python
# From wt/goto_cmd.py
project_path = get_worktree_project(repo.repo_dir, worktree_name, ctx.git)
if project_path is not None:
    target_path = worktree_path / project_path
else:
    target_path = worktree_path
```

This uses the `worktrees.toml` metadata file to store/retrieve project associations.

### Relative Path Pattern (checkout, up, down)

Navigation commands can preserve the user's relative position within a worktree by:

1. **Computing relative path from current worktree root to cwd**

   ```python
   # Get current position relative to worktree root
   current_worktree_root = find_worktree_for_path(ctx.cwd)
   relative_position = ctx.cwd.relative_to(current_worktree_root)
   ```

2. **Applying that path to target worktree**

   ```python
   # Navigate to same relative position in target
   target_path = target_worktree_root / relative_position
   ```

3. **Falling back to worktree root if path doesn't exist**

   ```python
   # Fall back if the relative path doesn't exist in target
   if target_path.exists():
       final_destination = target_path
   else:
       final_destination = target_worktree_root
   ```

This pattern allows users to stay in `src/components/` when switching worktrees, rather than always landing at the worktree root.

### Implementation Notes

- Use `render_activation_script()` in `activation.py` for script generation
- The computed path should be validated before navigation
- Log the fallback case so users understand why they landed at root

## Related Topics

- [Glossary: Project Context](../glossary.md#project-context) - What project context contains
- [Template Variables](../cli/template-variables.md) - Variables available in project configs
- [Shell Integration Patterns](shell-integration-patterns.md) - Script generation for shell commands
