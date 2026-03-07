---
title: Session Accumulation Architecture
read_when:
  - "working with push-session or fetch-sessions exec commands"
  - "modifying the learn pipeline session discovery"
  - "debugging session data on planned-pr-context branches"
tripwires:
  - action: "modifying manifest format without updating version field"
    warning: "Manifest includes a version field for forward compatibility. Increment on schema changes."
  - action: "assuming sessions are stored locally"
    warning: "Sessions are accumulated on git branches (planned-pr-context/<plan-id>). Use fetch-sessions to download."
---

# Session Accumulation Architecture

Sessions from Claude Code are preprocessed (JSONL to compressed XML, ~84% compression) and accumulated on git branches for async learn processing.

## Branch Naming

Each plan gets a dedicated branch: `planned-pr-context/<plan-id>` (e.g., `planned-pr-context/2521`).

## Manifest Format

```json
{
  "version": 1,
  "plan_id": 2521,
  "sessions": [
    {
      "session_id": "abc-123",
      "stage": "impl",
      "source": "local",
      "uploaded_at": "2026-03-01T...",
      "files": ["impl-abc123.xml"]
    }
  ]
}
```

## Lifecycle Stages

Three stages map to the plan lifecycle:

| Stage      | When                  | Trigger Command                 |
| ---------- | --------------------- | ------------------------------- |
| `planning` | During plan creation  | `/erk:plan-save` (Step 5)       |
| `impl`     | During implementation | `/erk:plan-implement` (Step 10) |
| `address`  | During PR review      | `/erk:pr-address` (Phase 6)     |

## Source Types

- `local`: Uploaded from Claude Code sessions
- `remote`: Uploaded from GitHub Actions workflows

## Idempotency

Duplicate `session_id` entries are replaced, not appended. Re-uploading the same session is safe.

## Key Commands

- `erk exec push-session`: Preprocesses and pushes a session to the planned-pr-context branch
- `erk exec fetch-sessions`: Downloads sessions from a planned-pr-context branch

## Graceful Degradation

Push failures return `{"uploaded": false, "reason": "..."}` and never hard-fail. Session upload is a non-critical operation -- implementation continues regardless.

**Source:** `src/erk/cli/commands/exec/scripts/push_session.py`

## Gateway Enhancement

`read_file_from_ref()` reads files from git refs without checkout, enabling session data access without switching branches.

## Related Documentation

- [Planning Workflow](../planning/) - Plan lifecycle stages
