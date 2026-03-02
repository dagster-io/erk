---
title: Land-Learn Integration
read_when:
  - "modifying the erk land command's learn workflow"
  - "debugging session discovery during land"
  - "working with session reporting in the land pipeline"
  - "learn plan creation"
  - "session discovery"
  - "empty learn plan"
tripwires:
  - action: "making session discovery failures block the land command"
    warning: "Session discovery uses fire-and-forget error resilience. The entire learn workflow is wrapped in try/except to prevent blocking land. Failures are reported as warnings, never errors."
    score: 6
  - action: "modifying learn plan skip guards in land_learn.py"
    warning: "Learn plan creation may skip silently when no sessions exist. Check land-learn-integration.md before modifying skip guards."
---

# Land-Learn Integration

After landing a PR, `erk land` optionally creates a learn plan to capture implementation insights. The session discovery step reports what sessions are available for the learn workflow.

## Skip Guards

Learn plan creation skips in two scenarios:

1. **No sessions tracked at all** — e.g., manual CHANGELOG PRs or PRs without implementation sessions. The `all_session_ids` list is empty because no planning, implementation, or learn sessions were recorded.

2. **Sessions exist but XML extraction produces no content** — Sessions were tracked in GitHub metadata but preprocessing produced no usable XML (warmup sessions, empty sessions, or sessions that fail to parse).

<!-- Source: src/erk/cli/commands/land_learn.py, _create_learn_pr_impl -->

See `_create_learn_pr_impl()` in `src/erk/cli/commands/land_learn.py` — the guard uses the emptiness of `all_session_ids` to distinguish between the two cases and display different debug messages: "(no sessions were tracked for this plan)" when no sessions exist at all, or "(sessions found but no XML could be extracted)" when sessions were tracked but preprocessing produced nothing.

## Session Discovery Pipeline

The pipeline flows through several stages:

<!-- Source: packages/erk-shared/src/erk_shared/sessions/discovery.py -->
<!-- Source: src/erk/cli/commands/land_learn.py:211-307 -->

1. **`SessionsForPlan`** — Frozen dataclass with three session ID collections:
   - `planning_session_id: str | None` (0 or 1)
   - `implementation_session_ids: list[str]`
   - `learn_session_ids: list[str]`
   - `all_session_ids()` method returns deduplicated list in order: planning → impl → learn

2. **`get_readable_sessions()`** — Filters to sessions with readable JSONL files on disk. Returns `list[tuple[str, Path]]`.

3. **`_compute_session_stats()`** — Preprocesses each session:
   - Reads JSONL and extracts user turns, duration, raw size
   - Runs preprocessing pipeline (deduplication, truncation)
   - Chunks XML with 200,000 token limit
   - Returns `SessionStats` with `xml_chunks: tuple[str, ...]`, or `None` if session is empty/unparseable

4. **Type prefixing** — Each session gets a filename prefix based on its type:
   - `planning-{sid}.xml` for planning sessions
   - `impl-{sid}.xml` for implementation sessions
   - `learn-{sid}.xml` for learn sessions
   - `unknown-{sid}.xml` as fallback

5. **Multi-chunk naming** — Sessions exceeding the token limit are split:
   - Single chunk: `{prefix}-{sid}.xml`
   - Multiple chunks: `{prefix}-{sid}-part{N}.xml` (N starts at 1)

## Cycle Prevention

Plans with the `erk-learn` label skip learn plan creation to prevent infinite loops:

<!-- Source: src/erk/cli/commands/land_learn.py, _maybe_create_learn_pr -->

See `_maybe_create_learn_pr()` in `src/erk/cli/commands/land_learn.py` — it checks whether `"erk-learn"` is in the plan's labels and returns early if so. Learn plans themselves are created with labels `["erk-pr", "erk-learn"]`, so landing a learn plan does not trigger another learn plan.

## Session Discovery Logging

<!-- Source: src/erk/cli/commands/land_learn.py:211-307, _log_session_discovery -->

`_log_session_discovery()` in `land_learn.py:211-307` reports session discovery results and returns a `dict[str, str]` mapping file paths to XML content. Each key follows the naming convention `.erk/impl-context/sessions/{type}-{session_id}.xml` (with `-part{N}` suffix for multi-chunk sessions). The dict feeds into `create_plan_draft_pr(extra_files=...)` to embed session XML in the learn plan PR diff.

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

<!-- Source: src/erk/cli/commands/land_learn.py, _create_learn_pr_with_sessions -->

See `_create_learn_pr_with_sessions()` in `src/erk/cli/commands/land_learn.py` for the fire-and-forget wrapper. The entire learn workflow is wrapped in a try/except that catches all exceptions and emits a warning instead of raising. This ensures that learn failures never block the primary `erk land` operation. A failed learn plan is a warning, not an error.

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
- [Learn Plan Metadata Fields](../planning/learn-plan-metadata-fields.md) — Metadata fields on learn plans
