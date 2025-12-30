---
title: Issue Reference Flow
read_when:
  - "issue references not appearing in PRs"
  - "debugging 'Closes #N' in PR body"
  - "working with issue.json"
---

# Issue Reference Flow

This document describes how issue references flow through the erk system, from creation to consumption in PR bodies.

## Creation

The `save_issue_reference(impl_dir, issue_number, issue_url)` function writes to `issue.json`.

Called by:

- `create_worker_impl_folder()` - For remote implementation
- `erk wt create --from-plan` - For local implementation

## Reading

Two functions in `erk_shared/impl_folder.py`:

- `has_issue_reference(impl_dir)` - Checks if issue.json exists
- `read_issue_reference(impl_dir)` - Returns IssueReference dataclass

## Consumers

Commands that should auto-read from `.impl/issue.json`:

| Command              | Auto-reads? | Purpose                     |
| -------------------- | ----------- | --------------------------- |
| `finalize.py`        | ✅ Yes      | Adds 'Closes #N' to PR body |
| `get-pr-body-footer` | ✅ Yes      | Generates PR footer text    |

## Anti-Pattern

**Don't require explicit `--issue-number` when `.impl/issue.json` exists.**

This creates unnecessary coupling between callers and the issue reference system. Commands should transparently read from the standard location.

## Data Flow Diagram

```
┌─────────────────────┐
│ create_worker_impl  │
│ or wt create        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ .impl/issue.json    │
│ {                   │
│   "number": 123,    │
│   "url": "..."      │
│ }                   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ finalize.py         │
│ get-pr-body-footer  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ PR Body:            │
│ "Closes #123"       │
└─────────────────────┘
```

## Related Topics

- [PR Finalization Paths](pr-finalization-paths.md) - Local vs remote PR submission
- [Implementation Folder Lifecycle](impl-folder-lifecycle.md) - Folder structure and lifecycle
