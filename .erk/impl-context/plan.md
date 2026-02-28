# Plan: Restore Rich Session Discovery Logging in `erk land`

## Context

PR #8437 restored basic session discovery logging to `erk land`, but the output is minimal compared to what `trigger_async_learn.py` (lines 387-415, 483-488) previously showed. The old code had per-session type badges, source type indicators, and individual file sizes. The current code just shows generic bullet points and an aggregated KB total.

## Target Output

**Current:**
```
  📋 Discovered 2 session(s): 1 planning, 1 impl
     - aaaa1111...
     - bbbb2222...
  📂 2/2 session(s) available locally (2,048 KB JSONL)
```

**Enhanced (matching old trigger_async_learn.py style):**
```
  📋 Discovered 2 session(s): 1 planning, 1 impl
     📝 planning: aaaa1111... (local, 512 KB)
     🔧 impl:     bbbb2222... (local, 566 KB)
```

When a session isn't locally available:
```
     🔧 impl:     cccc3333... (not found)
```

## Implementation

### Step 1: Modify `_log_session_discovery` in `land_learn.py`

**File:** `src/erk/cli/commands/land_learn.py` (lines 58-87)

Changes:
- Keep the summary line unchanged
- Build a `readable_map: dict[str, Path]` from `get_readable_sessions()` for O(1) lookup
- Classify each session as planning/impl/learn using set membership
- Replace generic `- {sid[:8]}...` bullets with typed lines: `📝 planning: aaaa1111... (local, 512 KB)`
- Use `click.style(..., dim=True)` for the parenthetical source/size info
- Remove the separate "📂 available locally" aggregated line (per-session info subsumes it)

### Step 2: Update tests in `test_land_learn.py`

**File:** `tests/unit/cli/commands/land/test_land_learn.py`

- `test_log_planning_and_impl_sessions` (line 326): Assert emoji badges `📝`/`🔧` and labels appear
- `test_log_includes_learn_count` (line 347): Assert `📚` learn badge appears
- `test_log_local_session_sizes` (line 364): Replace aggregated assertions with per-session assertions (check for `local` and `KB` per session, remove `"session(s) available locally"` check)

### Step 3: Add test for mixed local/not-found scenario

New test `test_log_session_mixed_local_and_not_found` with one locally available session and one missing, verifying both `local` and `not found` appear.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/land_learn.py` | Enhance `_log_session_discovery` (lines 58-87) |
| `tests/unit/cli/commands/land/test_land_learn.py` | Update 3 existing tests, add 1 new test |

## Reference

- Old rich code: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` lines 387-415
- Reuse: `get_readable_sessions` from `erk_shared.sessions.discovery`

## Verification

1. Run `uv run pytest tests/unit/cli/commands/land/test_land_learn.py`
2. Run `uv run ruff check src/erk/cli/commands/land_learn.py`
3. Run `uv run ty check src/erk/cli/commands/land_learn.py`
