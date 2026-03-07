---
title: Session Storage Architecture
read_when:
  - "proposing changes to session storage mechanism"
  - "understanding how sessions are pushed and retrieved"
  - "working with push-session exec script"
tripwires:
  - action: "proposing branch-based session storage as a new idea"
    warning: "Session storage IS branch-based (planned-pr-context/{plan_id} branches). An earlier attempt at a different branch-based approach was tried and reverted in PR #7757→#7765. The current branch-based approach (push_session.py) is the stable implementation."
---

# Session Storage Architecture

Sessions are stored on dedicated git branches and referenced via plan metadata. This design evolved through a same-day iteration cycle.

## Current Implementation

`push_session.py` preprocesses session JSONL to compressed XML and pushes to a `planned-pr-context/{plan_id}` branch, accumulating multiple sessions across lifecycle stages. Plan metadata is updated with:

| Metadata Field        | Value                          |
| --------------------- | ------------------------------ |
| `last_session_branch` | `planned-pr-context/{plan_id}` |
| `last_session_id`     | Claude Code session ID         |
| `last_session_at`     | ISO timestamp                  |
| `last_session_source` | `"local"` or `"remote"`        |

## Historical Context

- **PR #7757**: Migrated sessions from gists to branch-based storage (initial attempt)
- **PR #7765**: Reverted the migration on the same day due to reliability issues
- **Current state**: Branch-based storage via `push_session.py` with `planned-pr-context/{plan_id}` branches — a refined approach that addressed the earlier issues

The current implementation differs from the reverted one in its use of dedicated `planned-pr-context/` branches (isolated from feature branches) and atomic force-push semantics.

## Code Location

`src/erk/cli/commands/exec/scripts/push_session.py` — full push flow including preprocessing, branch creation, session accumulation, and metadata update.
