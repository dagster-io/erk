---
title: Session Discovery Architecture
read_when:
  - "finding Claude Code sessions for a plan"
  - "implementing session lookup from GitHub issues"
  - "understanding dual-source discovery patterns"
---

# Session Discovery Architecture

Erk discovers Claude Code sessions associated with plans through a dual-source approach.

## Core Data Structure

```python
@dataclass(frozen=True)
class SessionsForPlan:
    planning_session_id: str | None  # From created_from_session in plan-header
    implementation_session_ids: list[str]  # From impl-started/ended comments
    learn_session_ids: list[str]  # From learn-invoked comments
```

## Discovery Sources

### Primary: GitHub Issue Metadata

Sessions are tracked in the plan issue:

- `created_from_session` field in plan-header → planning session
- `last_local_impl_session` field in plan-header → most recent impl
- `impl-started`/`impl-ended` comments → all implementation sessions
- `learn-invoked` comments → previous learn sessions

### Fallback: Local Filesystem

When GitHub has no tracked sessions (older issues), scan ~/.claude/projects/ for sessions where gitBranch matches P{issue}-\*.

## Key Functions

- `find_sessions_for_plan()` - Extracts sessions from GitHub issue
- `get_readable_sessions()` - Filters to sessions that exist on disk
- `find_local_sessions_for_project()` - Scans local sessions by branch pattern
