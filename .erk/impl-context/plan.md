# Plan: Add session preprocessing stats to `erk land` discovery output

## Context

During `erk land`, session discovery currently shows only raw JSONL file sizes:
```
  📋 Discovered 2 session(s): 1 planning, 1 impl
        📝  planning:  5acd806c...  (local, 515 KB)
        🔧  impl:      5968a0da...  (local, 695 KB)
```

This was previously richer -- the old `trigger_async_learn.py` (removed in `b94b466e9`) preprocessed sessions to XML during land and showed compression metrics (`📉 Token reduction: 78.5% (515,000 → 110,750 chars)`). That code was removed as part of a simplification that cut ~363 lines across 7 helpers.

We want to bring back preprocessing during land to show both raw JSONL and compressed XML sizes, plus user turns and duration. The preprocessing uses functions already available in `preprocess_session.py`.

## Target output

```
  📋 Discovered 2 session(s): 1 planning, 1 impl
        📝  planning:  5acd806c...  12 turns · 8 min  (515 KB → 89 KB)
        🔧  impl:      5968a0da...  34 turns · 22 min  (695 KB → 142 KB)
✓ Created learn plan #8461 for plan #8457
```

## Changes

### 1. Add `compute_session_stats()` to `land_learn.py`

Add a `SessionStats` frozen dataclass and `compute_session_stats()` function directly in `land_learn.py` (only consumer for now).

**`src/erk/cli/commands/land_learn.py`**

```python
@dataclass(frozen=True)
class SessionStats:
    user_turns: int
    duration_minutes: int | None
    raw_size_kb: int
    xml_size_kb: int
```

`compute_session_stats(session_path: Path, *, session_id: str)`:
- Count user entries with text content (using `iter_jsonl_entries` + `parse_session_timestamp` from `session_schema.py`)
- Compute duration from first/last timestamps
- Call the existing `_preprocess_session_direct()` from `preprocess_session.py` (the exec script module) to get XML sections, matching the old `trigger_async_learn.py` pattern
- Compute raw size: main JSONL + agent logs matching the session ID (via `discover_agent_logs`)
- Compute XML size: sum of XML section lengths

Key reusable functions from the exec script `preprocess_session.py`:
- `process_log_file()` - parse and filter JSONL entries
- `is_empty_session()`, `is_warmup_session()` - skip non-meaningful sessions
- `deduplicate_documentation_blocks()`, `truncate_tool_parameters()`, `deduplicate_assistant_messages()` - compression pipeline
- `discover_agent_logs()` - find agent logs for session
- `split_entries_to_chunks()` - generate chunked XML sections

This mirrors how the old `_preprocess_session_direct()` in `trigger_async_learn.py` worked (lines 155-230 of the deleted file).

### 2. Update `_log_session_discovery()` in `land_learn.py`

For each readable session, call `compute_session_stats()` and format the detail column:
```python
# Was: detail = f"[dim](local, {size_kb:,} KB)[/dim]"
# Now:
duration_part = f" · {stats.duration_minutes} min" if stats.duration_minutes is not None else ""
detail = f"[dim]{stats.user_turns} turns{duration_part}  ({stats.raw_size_kb:,} KB → {stats.xml_size_kb:,} KB)[/dim]"
```

### 3. Update tests in `test_land_learn.py`

Update `test_log_local_session_sizes` and `test_log_session_mixed_local_and_not_found`:
- Write realistic JSONL content to the fake session files (user + assistant entries with timestamps) so `compute_session_stats` can parse them
- Update assertions: check for `turns`, `→`, `KB` instead of `local`

## Files to modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/land_learn.py` | Add `SessionStats`, `compute_session_stats()`, update `_log_session_discovery()` |
| `tests/unit/cli/commands/land/test_land_learn.py` | Update session discovery tests with realistic JSONL content |

## Key functions to reuse

From `src/erk/cli/commands/exec/scripts/preprocess_session.py`:
- `process_log_file(path, session_id=..., enable_filtering=True)` → filtered entries
- `is_empty_session(entries)`, `is_warmup_session(entries)` → skip filters
- `deduplicate_documentation_blocks(entries)` → dedup docs
- `truncate_tool_parameters(entries)` → truncate params
- `deduplicate_assistant_messages(entries)` → dedup assistant text
- `discover_agent_logs(session_path, session_id)` → find agent JSONL files
- `split_entries_to_chunks(entries, max_tokens=..., source_label=..., enable_pruning=True)` → XML chunks

From `packages/erk-shared/src/erk_shared/learn/extraction/session_schema.py`:
- `iter_jsonl_entries(content)` → iterate JSONL lines
- `parse_session_timestamp(value)` → parse timestamps

## Verification

1. Run `pytest tests/unit/cli/commands/land/test_land_learn.py` to verify tests pass
2. Run `ruff check src/erk/cli/commands/land_learn.py` and `ty check src/erk/cli/commands/land_learn.py` for lint/type checks
3. Manual: run `erk land` on a plan with sessions and verify the output shows turns, duration, and compression stats
