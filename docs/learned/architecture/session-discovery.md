---
title: Session Discovery Architecture
read_when:
  - "finding Claude Code sessions for a plan"
  - "implementing session lookup from GitHub issues"
  - "understanding dual-source discovery patterns"
---

# Session Discovery Architecture

Erk discovers Claude Code sessions associated with plans through a dual-source approach: authoritative GitHub metadata first, local filesystem fallback second.

## Core Data Structure

The `SessionsForPlan` dataclass represents all sessions associated with a plan:

- `planning_session_id` - From `created_from_session` field in plan-header metadata
- `implementation_session_ids` - From `impl-started`/`impl-ended` issue comments
- `learn_session_ids` - From `learn-invoked` issue comments

See `packages/erk-shared/src/erk_shared/sessions/discovery.py` for the canonical implementation.

## Discovery Sources

### Primary: GitHub Issue Metadata

Sessions are tracked in the plan issue through:

1. **Plan header metadata** - `created_from_session` field stores the planning session ID
2. **Implementation comments** - `impl-started` and `impl-ended` comments track implementation sessions
3. **Learn comments** - `learn-invoked` comments track previous learn invocations

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

## Pattern: Dual-Source Discovery

This pattern appears throughout erk when data can come from multiple sources:

1. **Check authoritative source first** (GitHub issue metadata)
2. **Fallback to local scan** when authoritative source lacks data
3. **Merge results** if both sources provide partial information

This enables:

- Cross-machine workflows (GitHub is authoritative)
- Backwards compatibility (older issues without metadata)
- Offline resilience (local fallback when GitHub unavailable)

## Related Topics

- [Impl Folder Lifecycle](impl-folder-lifecycle.md) - How .impl/ tracks implementation state
- [Markers](markers.md) - How impl-started/ended comments are created
