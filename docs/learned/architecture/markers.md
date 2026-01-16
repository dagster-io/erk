---
title: Marker System
read_when:
  - "creating worktree state tracking"
  - "adding friction before destructive operations"
  - "implementing pending learn workflow"
---

# Marker System

Markers are empty files in `.erk/scratch/__erk_markers/` that signal worktree state conditions.

## Purpose

Markers provide friction before destructive operations. They persist across sessions and block actions until explicitly cleared.

## Current Markers

| Marker          | Created By    | Cleared By                                    | Purpose                                          |
| --------------- | ------------- | --------------------------------------------- | ------------------------------------------------ |
| `pending-learn` | `erk land` | `erk plan learn`, `create-learn-plan` kit CLI | Block worktree deletion until insights extracted |

## API

Located in `erk_shared/scratch/markers.py`:

- `create_marker(worktree_path, marker_name)` - Create marker file
- `marker_exists(worktree_path, marker_name)` - Check if marker exists
- `delete_marker(worktree_path, marker_name)` - Delete marker if exists
- `get_marker_path(worktree_path, marker_name)` - Get path to marker file

## Usage Pattern

1. **Create marker** when starting an operation that requires follow-up
2. **Check marker** before destructive operations (e.g., worktree deletion)
3. **Delete marker** when follow-up is complete

## Example: Pending Learn Flow

1. `erk land` merges PR → creates `pending-learn` marker
2. User tries `erk wt delete` → blocked with "run learn first"
3. User runs learn → marker deleted
4. User can now delete worktree
