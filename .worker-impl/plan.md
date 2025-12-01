# Plan: Display Fetch Duration in Dashboard Footer

## Goal

Add data fetch duration to the dashboard status bar so users can see how long each refresh took.

**Current footer:**

```
Found 30 plan(s) | Updated: 15:21:15 | Next refresh: 2s | Ctrl+C to exit
```

**Target footer:**

```
Found 30 plan(s) | Updated: 15:21:15 (1.2s) | Next refresh: 2s | Ctrl+C to exit
```

## Implementation Steps

### Step 1: Update `_build_watch_content()` signature

Add `fetch_duration_secs: float | None` parameter to accept the fetch duration.

**File:** `src/erk/cli/commands/plan/list_cmd.py` (lines 444-469)

```python
def _build_watch_content(
    table: Table | None,
    count: int,
    last_update: str,
    seconds_remaining: int,
    fetch_duration_secs: float | None = None,  # NEW
) -> Group | Panel:
```

### Step 2: Update footer format string

Modify the footer to include duration when available:

```python
# Build duration suffix
duration_suffix = f" ({fetch_duration_secs:.1f}s)" if fetch_duration_secs is not None else ""

footer = (
    f"Found {count} plan(s) | Updated: {last_update}{duration_suffix} | "
    f"Next refresh: {seconds_remaining}s | Ctrl+C to exit"
)
```

### Step 3: Time the fetch in `_run_watch_loop()`

Use `ctx.time.now()` to measure fetch duration:

**File:** `src/erk/cli/commands/plan/list_cmd.py` (lines 472-513)

```python
# Initial data fetch - with timing
start = ctx.time.now()
table, count = build_table_fn()
fetch_duration_secs = (ctx.time.now() - start).total_seconds()
last_update = ctx.time.now().strftime("%H:%M:%S")

# ... in the countdown update call:
content = _build_watch_content(table, count, last_update, seconds_remaining, fetch_duration_secs)

# ... in the refresh block:
if seconds_remaining <= 0:
    start = ctx.time.now()
    table, count = build_table_fn()
    fetch_duration_secs = (ctx.time.now() - start).total_seconds()
    last_update = ctx.time.now().strftime("%H:%M:%S")
    seconds_remaining = int(interval)
```

### Step 4: Update tests

Update existing tests in `tests/commands/test_dash_watch.py`:

1. **Update `_build_watch_content()` calls** in tests to include the new parameter (can use `None` for backwards compatibility)

2. **Add test for duration display:**

```python
def test_build_watch_content_shows_fetch_duration() -> None:
    """Footer includes fetch duration when provided."""
    table = Table()
    content = _build_watch_content(
        table, count=5, last_update="14:30:45",
        seconds_remaining=3, fetch_duration_secs=1.234
    )
    # Verify duration appears in footer (will show "1.2s")
    assert isinstance(content, Group)
```

3. **Add test for watch loop timing:**

```python
def test_watch_loop_tracks_fetch_duration() -> None:
    """Watch loop measures and displays fetch duration."""
    # Use FakeTime with controlled now() increments
    # Verify footer contains duration in "X.Xs" format
```

## Files to Modify

| File                                    | Change                                    |
| --------------------------------------- | ----------------------------------------- |
| `src/erk/cli/commands/plan/list_cmd.py` | Add timing and update footer format       |
| `tests/commands/test_dash_watch.py`     | Update existing tests, add duration tests |

## Duration Format

Using seconds with one decimal (`1.2s`):

- Matches the countdown format style
- Easy to read at a glance
- Format: `f"{duration:.1f}s"` where duration is float seconds
