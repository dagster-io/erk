---
title: Session Discovery Architecture
read_when:
  - "finding Claude Code sessions for a plan"
  - "implementing session lookup from GitHub issues"
  - "understanding dual-source discovery patterns"
  - "working with branch-based session storage"
  - "downloading remote sessions for learn workflow"
last_audited: "2026-02-16 08:00 PT"
audit_result: clean
---

# Session Discovery Architecture

Erk discovers Claude Code sessions associated with plans through branch-based storage on `async-learn/{plan_id}` branches, with local filesystem fallback for backwards compatibility.

## Core Data Structure

The `SessionsForPlan` dataclass represents all sessions associated with a plan:

- `planning_session_id` - From `created_from_session` field in plan-header metadata
- `implementation_session_ids` - From `impl-started`/`impl-ended` issue comments
- `learn_session_ids` - From `learn-invoked` issue comments
- `last_session_branch` - Branch containing accumulated session XMLs
- `last_session_id` - Session ID of latest pushed session
- `last_session_source` - "local" or "remote" indicating session origin

See `packages/erk-shared/src/erk_shared/sessions/discovery.py` for the canonical implementation.

## Branch-Based Session Storage

Sessions are preprocessed (JSONL to compressed XML) and accumulated on `async-learn/{plan_id}` branches with manifest-based tracking. Each lifecycle stage (planning, impl, address) appends to the same branch.

### Plan Header Fields

The plan-header metadata tracks the latest session:

| Field                 | Description                                |
| --------------------- | ------------------------------------------ |
| `last_session_branch` | Branch containing accumulated session XMLs |
| `last_session_id`     | Claude Code session ID                     |
| `last_session_at`     | ISO 8601 timestamp when session was stored |
| `last_session_source` | "local" or "remote" indicating origin      |

### Push Flow

Sessions are pushed via `erk exec push-session`:

1. Preprocess session JSONL to compressed XML
2. Push to `async-learn/{plan_id}` branch, accumulating with existing sessions
3. Update plan-header metadata with session info

The CI workflow (`plan-implement.yml`) pushes sessions after implementation:

```bash
erk exec push-session \
  --session-file "$SESSION_FILE" \
  --session-id "$SESSION_ID" \
  --source remote \
  --plan-id "$PLAN_ID" \
  --stage impl
```

### Download Flow

Remote sessions are downloaded via `erk exec fetch-sessions`:

1. Fetch manifest and preprocessed XMLs from the `async-learn/{plan_id}` branch
2. Write XML files to the learn output directory
3. Return JSON with file list and manifest metadata

## Discovery Sources

### Primary: GitHub Issue Metadata

Sessions are tracked in the plan issue through:

1. **Plan header branch fields** - `last_session_branch` stores the `async-learn/{plan_id}` branch reference
2. **Plan header metadata** - `created_from_session` field stores the planning session ID
3. **Implementation comments** - `impl-started` and `impl-ended` comments track implementation sessions
4. **Learn comments** - `learn-invoked` comments track previous learn invocations

This approach makes GitHub the authoritative source, enabling cross-machine session discovery.

### Fallback: Local Filesystem

When GitHub has no tracked sessions (older issues created before session tracking), scan `~/.claude/projects/` for sessions where `gitBranch` matches `P{issue}-*`.

Use `find_local_sessions_for_project()` for this fallback path.

## Key Functions

| Function                            | Purpose                                          |
| ----------------------------------- | ------------------------------------------------ |
| `find_sessions_for_plan()`          | Extract session IDs from GitHub issue metadata   |
| `get_readable_sessions()`           | Filter to sessions that exist on local disk      |
| `find_local_sessions_for_project()` | Scan local sessions by branch pattern (fallback) |
| `extract_implementation_sessions()` | Parse impl session IDs from issue comments       |
| `extract_learn_sessions()`          | Parse learn session IDs from issue comments      |

### Session Source Abstraction

The `SessionSource` ABC provides a uniform interface for session metadata:

| Class                 | Use Case                                       |
| --------------------- | ---------------------------------------------- |
| `LocalSessionSource`  | Sessions from `~/.claude/projects/` on machine |
| `RemoteSessionSource` | Sessions downloaded from gists                 |

Both provide: `source_type`, `session_id`, `run_id` (remote only), and `path`.

## Pattern: Dual-Source Discovery

This pattern appears throughout erk when data can come from multiple sources:

1. **Check authoritative source first** (GitHub issue metadata with branch info)
2. **Fallback to local scan** when authoritative source lacks data
3. **Merge results** if both sources provide partial information

This enables:

- Cross-machine workflows (GitHub is authoritative)
- Backwards compatibility (older issues without metadata)
- Offline resilience (local fallback when GitHub unavailable)

## Related Topics

- [Impl Folder Lifecycle](impl-folder-lifecycle.md) - How .erk/impl-context/ tracks implementation state
- [Markers](markers.md) - How impl-started/ended comments are created
- [Session Storage Architecture](session-storage-revert-rationale.md) - Branch-based session storage design and history
