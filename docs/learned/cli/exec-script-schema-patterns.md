---
title: Exec Script Schema Patterns
read_when:
  - "writing an exec script that produces JSON consumed by another script"
  - "debugging silent filtering failures in exec script pipelines"
  - "adding new fields to exec script JSON output"
tripwires:
  - action: "using dict .get() to access fields from exec script JSON output without a TypedDict schema"
    warning: "Silent filtering failures occur when field names are mistyped. Define TypedDict in erk_shared and use `cast()` in consumers."
  - action: "adding a new exec script that produces JSON consumed by another exec script"
    warning: "Define shared TypedDict in `packages/erk-shared/` for type-safe schema. Both producer and consumer import from the same schema definition."
  - action: "filtering session sources without logging which sessions were skipped and why"
    warning: "Silent filtering makes debugging impossible. Log to stderr when skipping sessions, include the reason (empty/warmup/filtered)."
---

# Exec Script Schema Patterns

When exec scripts produce JSON consumed by other scripts, field name typos cause silent failures. TypedDict schemas eliminate this class of bugs.

## Problem

Exec scripts often chain together: one produces JSON, another consumes it. Dict `.get()` access silently returns `None` for misspelled field names, causing downstream logic to filter out valid data.

Example of the bug this pattern prevents:

```python
# Producer outputs: {"session_source": "local"}
# Consumer tries to access: result.get("source_type")  # Wrong field name!
# Result: None returned, session silently filtered
```

## Pattern: TypedDict Schema in erk_shared

Define the JSON schema as a TypedDict in `packages/erk-shared/src/erk_shared/`, not in the producer or consumer.

**Why erk_shared?** Both producer and consumer import the same schema. Single source of truth prevents drift.

See `GetLearnSessionsResultDict` and `SessionSourceDict` in `packages/erk-shared/src/erk_shared/learn/extraction/get_learn_sessions_result.py:14-32` and `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py:16-24`.

## Consumer Pattern: cast() for Type Safety

Use `cast()` to narrow the dict type after JSON parsing:

```python
from typing import cast
from erk_shared.learn.extraction.get_learn_sessions_result import (
    GetLearnSessionsResultDict,
)

# After JSON parsing
sessions_result = _run_subprocess([...])
sessions = cast(GetLearnSessionsResultDict, sessions_result)

# Now typed access with autocomplete and type checking
session_sources = sessions["session_sources"]  # Type: list[SessionSourceDict]
```

See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:187-189` for the full pattern.

## LBYL Guards: Type Check → Value Check → Presence Check

Before accessing nested fields, check type, then value, then presence:

```python
for source_item in session_sources:
    # 1. Type check
    if not isinstance(source_item, dict):
        continue

    # 2. Value check (for discriminated unions)
    if source_item.get("source_type") != "local":
        continue

    # 3. Presence check
    session_path = source_item.get("path")
    if not isinstance(session_path, str):
        continue

    # Now safe to use session_path
```

See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:200-209` for this pattern in context.

## Session Type Determination: Compare IDs, Not Schema Fields

To determine if a session is a planning session or implementation session, **compare session IDs**:

```python
session_id = source_item.get("session_id")
planning_session_id = sessions["planning_session_id"]
prefix = "planning" if session_id == planning_session_id else "impl"
```

**Why not a schema field?** The schema describes session _sources_ (where they came from), not session _types_ (what role they played). Session type is derived from comparing IDs.

See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:211-213`.

## Empty Output Handling: Treat as Valid, Not Error

When preprocessing returns empty output (empty session, warmup session), treat it as a valid case, not an error:

```python
output_paths = _run_preprocess_session([...])

if not output_paths:
    click.echo(
        "[trigger-async-learn] Session filtered (empty/warmup), skipping",
        err=True,
    )
    continue  # Not an error, just skip this session
```

See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:231-236`.
