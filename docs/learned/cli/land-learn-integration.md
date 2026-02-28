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

<!-- Source: src/erk/cli/commands/land_learn.py:58-87, _log_session_discovery -->

`_log_session_discovery()` in `src/erk/cli/commands/land_learn.py:58-87` reports session discovery results to the user:

```python
def _log_session_discovery(
    ctx: ErkContext,
    *,
    sessions: SessionsForPlan,
    all_session_ids: list[str],
) -> None:
```

### Output Format

The function produces a structured summary:

```
  📋 Discovered 3 session(s): 1 planning, 2 impl
     - abc12345...
     - def67890...
     - ghi24680...
  📂 2/3 session(s) available locally (1,234 KB JSONL)
```

### Session Type Counting

Sessions are categorized by type from the `SessionsForPlan` object:

- **Planning**: 0 or 1 (from `sessions.planning_session_id`)
- **Impl**: count of `sessions.implementation_session_ids`
- **Learn**: count of `sessions.learn_session_ids` (only shown if non-zero)

### Local File Availability

The function checks which sessions have readable JSONL files locally via `get_readable_sessions()`. It reports the count and total size in KB, giving users visibility into how much session data is available for the learn workflow.

## Fire-and-Forget Error Resilience

The entire learn workflow in the land command is wrapped in a try/except:

```python
try:
    _create_learn_pr_impl(ctx, state=state)
except Exception as exc:
    user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")
```

This ensures that learn failures never block the primary `erk land` operation. A failed learn plan is a warning, not an error.

## Related Documentation

- [Learn Workflow](../planning/learn-workflow.md) — Full learn pipeline documentation
- [Session Discovery](../architecture/session-discovery.md) — How sessions are discovered from metadata
