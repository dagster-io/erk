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
---

# Land-Learn Integration

After landing a PR, `erk land` optionally creates a learn plan to capture implementation insights. The session discovery step reports what sessions are available for the learn workflow.

## Skip Guards

The learn plan creation pipeline has multiple skip guards that prevent unnecessary work:

<!-- Source: src/erk/cli/commands/land_learn.py:351-383 -->

1. **No plan ID** (`land_learn.py:351-353`): Early return if `plan_id is None`
2. **Config disabled** (`land_learn.py:356-357`): Respects `_should_create_learn_pr()` config check
3. **Plan not found** (`land_learn.py:361-362`): Returns if plan cannot be fetched
4. **Cycle prevention** (`land_learn.py:363-364`): Plans with `erk-learn` label skip learn plan creation (see below)
5. **No session material** (`land_learn.py:373-383`): Skip if no XML chunks were extracted
   - Distinguishes between "no sessions tracked at all" (e.g., manual CHANGELOG PRs) and "sessions found but XML extraction produced no content" (warmup/empty sessions)

## Session Discovery Pipeline

The pipeline flows through four stages:

### Stage 1: Session Lookup

<!-- Source: src/erk/cli/commands/land_learn.py:367-368 -->

`SessionsForPlan` is created from plan backend metadata containing:

- `planning_session_id` (str | None): 0 or 1 planning session
- `implementation_session_ids` (list[str]): impl sessions
- `learn_session_ids` (list[str]): prior learn sessions (only shown if non-zero)

### Stage 2: Local File Availability

`get_readable_sessions()` filters to sessions with readable JSONL files on disk via `claude_installation.find_session_globally()`. Reports count and total size in KB.

### Stage 3: Stats and Preprocessing

`_compute_session_stats()` (`land_learn.py:70-156`) runs the full compression pipeline per session:

1. Parses JSONL to count user turns and compute duration
2. Runs `process_log_file()` -> `deduplicate_documentation_blocks()` -> `truncate_tool_parameters()` -> `deduplicate_assistant_messages()`
3. Calls `split_entries_to_chunks()` with 200k token limit
4. Returns `SessionStats` with `xml_chunks: tuple[str, ...]`

### Stage 4: XML File Collection

<!-- Source: src/erk/cli/commands/land_learn.py:282-295 -->

XML chunks are collected into files with type-prefixed names:

**Type prefixing** (`_session_type_prefix()` at `land_learn.py:194-208`):

- `planning-{sid}.xml` for planning sessions
- `impl-{sid}.xml` for implementation sessions
- `learn-{sid}.xml` for learn sessions

**Multi-chunk naming**: When a session produces multiple chunks:

- Single chunk: `{prefix}-{sid}.xml`
- Multiple chunks: `{prefix}-{sid}-part{N}.xml` (N starts at 1)

## Session Discovery Logging

<!-- Source: src/erk/cli/commands/land_learn.py:58-87, _log_session_discovery -->

`_log_session_discovery()` produces a structured summary:

```
  session(s): 1 planning, 2 impl
     - abc12345...
     - def67890...
     - ghi24680...
  2/3 session(s) available locally (1,234 KB JSONL)
```

## Fire-and-Forget Error Resilience

<!-- Source: src/erk/cli/commands/land_learn.py:171-191 -->

The entire learn workflow in the land command is wrapped in a try/except via `_create_learn_pr_with_sessions()`:

```python
try:
    _create_learn_pr_impl(ctx, state=state)
except Exception as exc:
    user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")
```

This ensures that learn failures never block the primary `erk land` operation. A failed learn plan is a warning, not an error.

## Cycle Prevention

<!-- Source: src/erk/cli/commands/land_learn.py:363-364 -->

Plans with the `erk-learn` label skip learn plan creation. This prevents documentation cycles:

- `erk-plan` -> implement -> land -> `erk-learn` (correct flow)
- `erk-learn` -> land -> `erk-learn` (cycle, prevented by label check)

The guard at `land_learn.py:363-364` checks `if "erk-learn" in plan_result.labels: return`.

## Related Documentation

- [Learn Workflow](../planning/learn-workflow.md) -- Full learn pipeline documentation
- [Session Discovery](../architecture/session-discovery.md) -- How sessions are discovered from metadata
