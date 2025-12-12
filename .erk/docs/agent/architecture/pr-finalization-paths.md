---
title: PR Finalization Paths
read_when:
  - "debugging PR body content or issue closing"
  - "understanding local vs remote PR submission"
  - "working with 'Closes #N' in PRs"
---

# PR Finalization Paths

The erk system has two distinct code paths for finalizing PRs. Both should behave identically - the key principle is that commands should auto-read from `.impl/issue.json` rather than requiring explicit parameters.

## Local Path (Graphite)

- **Entry point:** `finalize.py` in `erk-shared`
- **Used when:** Running `gt ss` or local PR submission
- **Issue reference:** Auto-reads from `.impl/issue.json`
- **Behavior:** Adds 'Closes #N' to PR body if issue reference exists

## Remote Path (GitHub Actions)

- **Entry point:** `erk-impl.yml` workflow
- **Used when:** Running `erk submit` for remote queue
- **Issue reference:** Must be passed to commands OR auto-read from `.impl/issue.json`
- **PR body update:** Via `get-pr-body-footer` command

## Key Principle

Both paths should behave identically. Commands should auto-read from `.impl/issue.json` rather than requiring explicit parameters.

## Anti-Pattern

Requiring callers to explicitly pass `--issue-number` when `.impl/issue.json` exists. This creates unnecessary coupling and makes the remote path behave differently from the local path.

## Related Topics

- [Implementation Folder Lifecycle](impl-folder-lifecycle.md) - Folder structure and lifecycle
- [Issue Reference Flow](issue-reference-flow.md) - How issue references flow through the system
