# Learn Analysis: Plan #5067 - Phase 1 Session Source Abstraction

## Summary

This PR added plan-header metadata fields for tracking remote implementation details and learn status, along with a `SessionSource` abstraction to prepare for remote session support in Phase 2.

## Insights from Sessions

**[Impl]** The implementation was triggered by a user discussion about friction during `erk land` - the need to exit landing to run `erk learn` synchronously. This led to adding:
- `learn_status` field to track whether learning is pending/completed
- Expanded objective #4991 to include async learn at land time (Phase 3)

**[Impl]** The session source abstraction was designed as a "forward-looking stub" - `RemoteSessionSource` exists but Phase 2 will implement actual artifact download functionality.

## Documentation Items

### 1. Update plan-schema.md with learn_status field

**Location:** `docs/learned/planning/plan-schema.md`
**Action:** Update
**Source:** [Impl] - Field was added but not documented in schema reference

Add to the "Session tracking fields" table:

| Field | Type | Description |
|-------|------|-------------|
| `learn_status` | string\|null | Learning workflow status: "pending" (async learn triggered), "completed" (learn finished), or null (not tracked yet) |

Also update the example YAML to include `learn_status: null`.

### 2. Create session-sources.md documentation

**Location:** `docs/learned/sessions/session-sources.md`
**Action:** Create
**Source:** [Impl] - New architectural pattern

Document:
- **Purpose**: Abstraction for handling sessions from different origins (local vs remote artifacts)
- **Design insight**: Session files are always local during processing; the abstraction tracks where they *came from*
- **Classes**: `SessionSource` ABC, `LocalSessionSource`, `RemoteSessionSource` (stub)
- **Location**: `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py`
- **Testing**: `packages/erk-shared/tests/unit/learn/extraction/test_session_source.py`

### 3. No further updates needed

The following are already documented or don't need docs:
- `.claude/commands/erk/learn.md` - Already updated with new fields
- `last_remote_impl_run_id`, `last_remote_impl_session_id` - Already in plan-schema.md
- Internal extraction/update functions - Docstrings sufficient

## Verification

After implementing:
1. Check `docs/learned/planning/plan-schema.md` includes `learn_status` in Session tracking fields
2. Check `docs/learned/sessions/session-sources.md` exists with SessionSource documentation
3. Run `make format` to ensure documentation formatting

## Raw Materials

No gist created - implementation was straightforward with clear documentation needs identified from code review.