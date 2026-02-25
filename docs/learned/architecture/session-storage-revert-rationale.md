---
title: Session Storage Architecture
read_when:
  - "proposing changes to session storage mechanism"
  - "understanding how sessions are uploaded and retrieved"
  - "working with upload-session exec script"
tripwires:
  - action: "proposing branch-based session storage as a new idea"
    warning: "Session storage IS branch-based (async-learn/{plan_id} branches). An earlier attempt at a different branch-based approach was tried and reverted in PR #7757→#7765. The current branch-based approach (upload_session.py) is the stable implementation."
---

# Session Storage Architecture

Sessions are stored on dedicated git branches and referenced via plan metadata. This design evolved through a same-day iteration cycle.

## Current Implementation

<!-- Source: src/erk/cli/commands/exec/scripts/upload_session.py -->

`upload_session.py` creates an `async-learn/{plan_id}` branch from `origin/master`, commits the session JSONL file to `.erk/session/{session_id}.jsonl`, and force-pushes. Plan metadata is updated with:

| Metadata Field        | Value                   |
| --------------------- | ----------------------- |
| `last_session_branch` | `async-learn/{plan_id}` |
| `last_session_id`     | Claude Code session ID  |
| `last_session_at`     | ISO timestamp           |
| `last_session_source` | `"local"` or `"remote"` |

## Historical Context

- **PR #7757**: Migrated sessions from gists to branch-based storage (initial attempt)
- **PR #7765**: Reverted the migration on the same day due to reliability issues
- **Current state**: Branch-based storage via `upload_session.py` with `async-learn/{plan_id}` branches — a refined approach that addressed the earlier issues

The current implementation differs from the reverted one in its use of dedicated `async-learn/` branches (isolated from feature branches) and atomic force-push semantics.

## Code Location

<!-- Source: src/erk/cli/commands/exec/scripts/upload_session.py -->

`src/erk/cli/commands/exec/scripts/upload_session.py` — full upload flow including branch creation, JSONL commit, and metadata update.
