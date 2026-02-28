# Restore session discovery logging in `erk land`

## Context

When landing a PR, `erk land` creates a learn draft PR by calling `_create_learn_pr_impl` in `land_learn.py`. This function discovers session IDs associated with the plan (planning, impl, learn sessions) and lists them in the draft PR body.

Previously, the `erk land` pipeline had a complex async learn flow (~363 lines) that ran full JSONL→XML preprocessing with verbose output including:
- "📋 Discovering sessions..." with per-session type breakdowns
- "📉 Token reduction: XX.X% (N → M chars)" per session

This was removed in commit `2f667975a` ("Simplify learn trigger in `erk land`"). The new pipeline still discovers sessions but emits zero logging about them.

The user wants this logging restored. The JSONL→XML token savings are now calculated later by `/erk:learn`, not during land — so we'll add:
1. Session discovery summary (counts by type, IDs)
2. For locally available sessions: raw JSONL file sizes as a proxy for "data the learn step will process"

## Critical Files

- **`src/erk/cli/commands/land_learn.py`** — only file to change
  - `_create_learn_pr_impl()` lines 57–122: add logging after session discovery (line 79–80)
  - `ctx.claude_installation` is available on `ErkContext` (from `erk_shared.context.context`)

## Reusable Functions

- `get_readable_sessions(sessions_for_plan, claude_installation)` in `packages/erk-shared/src/erk_shared/sessions/discovery.py:74` — finds locally available sessions and their `Path`s. Use this to find which sessions have local JSONL files.
- `ctx.claude_installation` — already on `ErkContext`, passed as `ctx` into `_create_learn_pr_impl`

## Implementation

Add logging in `_create_learn_pr_impl` in `land_learn.py`, between the session discovery block and the "Build learn plan body" block (current line ~82):

```python
# Log session discovery summary
n_planning = 1 if sessions.planning_session_id else 0
n_impl = len(sessions.implementation_session_ids)
n_learn = len(sessions.learn_session_ids)
total = len(all_session_ids)
if total > 0:
    user_output(
        f"  📋 Discovered {total} session(s): "
        f"{n_planning} planning, {n_impl} impl"
        + (f", {n_learn} learn" if n_learn else "")
    )
    for sid in all_session_ids:
        user_output(f"     - {sid[:8]}...")

    # Show local JSONL file sizes for sessions we can reach
    readable = get_readable_sessions(sessions, ctx.claude_installation)
    if readable:
        total_bytes = sum(p.stat().st_size for _, p in readable)
        user_output(
            f"  📂 {len(readable)}/{total} session(s) available locally "
            f"({total_bytes // 1024:,} KB JSONL)"
        )
else:
    user_output("  ⚠️  No sessions discovered for this plan")
```

### Import addition

Add to `land_learn.py` imports:
```python
from erk_shared.sessions.discovery import get_readable_sessions
```

## Sample output

```
  📋 Discovered 2 session(s): 1 planning, 1 impl
     - ed51968a...
     - 2654b279...
  📂 2/2 session(s) available locally (1,234 KB JSONL)
✓ Created learn plan #8435 for plan #8432
```

## Verification

1. Run `erk land` on a PR with sessions associated
2. Confirm session count and IDs appear in output before "✓ Created learn plan"
3. Run unit tests: `pytest tests/unit/cli/commands/land/test_land_learn.py -x`
4. If `get_readable_sessions` needs mocking: `FakeClaudeInstallation` is already available in test infrastructure
