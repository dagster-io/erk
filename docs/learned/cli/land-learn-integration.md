---
title: Land-Learn Integration
read_when:
  - "modifying the erk land command's learn workflow"
  - "debugging session discovery during land"
  - "working with session reporting in the land pipeline"
tripwires:
  - action: "making session discovery failures block the land command"
    warning: "Session discovery uses fire-and-forget error resilience. The entire learn workflow is wrapped in try/except to prevent blocking land. Failures are reported as warnings, never errors."
    score: 6
---

# Land-Learn Integration

After landing a PR, `erk land` optionally creates a learn plan to capture implementation insights. The session discovery step reports what sessions are available for the learn workflow.

## Session Discovery Logging

<!-- Source: src/erk/cli/commands/land_learn.py:209-305, _log_session_discovery -->

See `_log_session_discovery()` in `src/erk/cli/commands/land_learn.py`. This function reports session discovery results and returns a file map of preprocessed session XML.

### Return Value

Returns `dict[str, str]` mapping file paths to XML content. Each key follows the naming convention `.erk/impl-context/sessions/{type}-{session_id}.xml` (with `-part{N}` suffix for multi-chunk sessions). The dict feeds into `create_plan_draft_pr(extra_files=...)` to embed session XML in the learn plan PR diff.

### Output Format

The function produces a structured summary with per-session type badges, turn counts, duration, and compression stats.

### Session Type Counting

Sessions are categorized by type from the `SessionsForPlan` object:

- **Planning**: 0 or 1 (from `sessions.planning_session_id`)
- **Impl**: count of `sessions.implementation_session_ids`
- **Learn**: count of `sessions.learn_session_ids` (only shown if non-zero)

Type prefixes in file names: `planning`, `impl`, `learn`, `unknown`.

### Local File Availability

The function checks which sessions have readable JSONL files locally via `get_readable_sessions()`. It reports the count and total size, giving users visibility into how much session data is available for the learn workflow.

## Session XML File Returns

<!-- Source: src/erk/cli/commands/land_learn.py, SessionStats -->

Each readable session is preprocessed inline via the full preprocessing pipeline:

1. Parse JSONL and count user turns
2. Compute duration from timestamps
3. Run preprocessing (deduplication, truncation)
4. Chunk XML output at 200,000 token limit

See `SessionStats` in `src/erk/cli/commands/land_learn.py` for the frozen dataclass capturing preprocessing metrics (user turns, duration, raw/XML sizes, and XML content chunks). Multi-chunk sessions produce files with `-part1`, `-part2` suffixes.

## File Inventory Logging

The file inventory logger reports all files committed to the learn plan PR, showing file paths and sizes with human-readable byte formatting (B or KB with thousands separator).

## Fire-and-Forget Error Resilience

The entire learn workflow in the land command is wrapped in a try/except:

```python
try:
    _create_learn_pr_impl(ctx, state=state)
except Exception as exc:
    user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")
```

This ensures that learn failures never block the primary `erk land` operation. A failed learn plan is a warning, not an error.

## TUI Learn Plan Toast

When `erk land` creates a learn plan, the TUI displays a toast notification. The integration works through output parsing:

1. `extract_learn_plan_number()` in `src/erk/tui/operations/logic.py` scans operation output lines with regex `r"Created learn plan #(\d+)"`
2. On match, the TUI shows a toast via `notify()` after successful land
3. **Cycle prevention**: When the TUI triggers a land, it passes `plan_id=None` for learn plans (`row.plan_id if not row.is_learn_plan else None`). This prevents learn plans from creating learn plans of their own.

<!-- Source: src/erk/tui/operations/logic.py, extract_learn_plan_number -->
<!-- Source: src/erk/tui/operations/workers.py, _land_pr_async -->

## Related Documentation

- [Learn Workflow](../planning/learn-workflow.md) — Full learn pipeline documentation
- [Session Discovery](../architecture/session-discovery.md) — How sessions are discovered from metadata
