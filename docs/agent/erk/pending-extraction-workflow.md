---
title: Pending Extraction Workflow
read_when:
  - "landing a PR with erk"
  - "understanding erk pr land behavior"
  - "blocked from deleting worktree"
  - "seeing pending-extraction error"
---

# Pending Extraction Workflow

When `erk pr land` merges a PR, it creates a "pending extraction" marker that provides friction before worktree cleanup.

## Workflow

1. **`erk pr land`** - Merges PR, creates `.erk/pending-extraction` marker
2. **Extract insights** - Run `/erk:create-raw-extraction-plan` to capture learnings
3. **Cleanup** - Run `erk down --delete-current` to remove worktree

## Why This Friction?

Sessions often contain valuable discoveries:

- Architectural insights
- API quirks and workarounds
- Failed approaches (what NOT to do)
- Undocumented behaviors

The marker ensures these aren't lost before extraction.

## Bypassing the Check

Use `--force` to skip extraction:

- `erk down --delete-current --force`
- `erk wt delete <name> --force`

## Implementation Details

The marker system uses simple file presence/absence:

- **Marker location**: `<worktree>/.erk/pending-extraction`
- **Creation**: Empty file created by `erk pr land`
- **Deletion**: Removed by `/erk:create-raw-extraction-plan`
- **Blocking**: Commands check `marker_exists()` before destructive operations

**Code reference**: `src/erk/core/markers.py`

## Related Topics

- [Glossary: pending-extraction marker](../glossary.md#pending-extraction-marker)
- [Marker Pattern](../architecture/marker-pattern.md) - Design principles for marker files
