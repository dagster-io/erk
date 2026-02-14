---
title: Exec Script Schema Patterns
read_when:
  - "writing an exec script that produces JSON consumed by another script"
  - "debugging silent filtering failures in exec script pipelines"
  - "adding new fields to exec script JSON output"
tripwires:
  - action: "using dict .get() to access fields from exec script JSON output without a TypedDict schema"
    warning: "Silent filtering failures occur when field names are mistyped. Define TypedDict in erk_shared and use cast() in consumers."
  - action: "adding a new exec script that produces JSON consumed by another exec script"
    warning: "Define shared TypedDict in packages/erk-shared/ for type-safe schema. Both producer and consumer import from the same schema definition."
  - action: "filtering session sources without logging which sessions were skipped and why"
    warning: "Silent filtering makes debugging impossible. Log to stderr when skipping sessions, include the reason (empty/warmup/filtered)."
last_audited: "2026-02-08"
audit_result: clean
---

# Exec Script Schema Patterns

Exec scripts often chain together through JSON: one script outputs structured data, another consumes it. The critical vulnerability is **silent filtering failures** when field names are mistyped—dict `.get()` returns `None` for wrong keys, causing downstream logic to silently skip valid data.

## The Problem: Misspelled Fields = Silent Data Loss

When a producer outputs `{"session_source": "local"}` but the consumer accesses `result.get("source_type")`, Python returns `None` silently. The consumer's filtering logic treats this as "skip this record," and you lose data without any error message.

**Why this is insidious**: The script succeeds with exit code 0. No exceptions. No warnings. You only discover the bug when investigating why expected data is missing from results.

## Pattern: TypedDict in erk_shared

<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/get_learn_sessions_result.py, GetLearnSessionsResultDict -->
<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/session_source.py, SessionSourceDict -->

Define the JSON schema as a TypedDict in `packages/erk-shared/`, not in either the producer or consumer. See `GetLearnSessionsResultDict` and `SessionSourceDict` in `packages/erk-shared/src/erk_shared/learn/extraction/`.

**Why erk_shared?** Single source of truth prevents schema drift. When producer and consumer import the same TypedDict, typos become type checker errors instead of silent runtime bugs. The producer serializes to dict, the consumer casts back, and `ty check` validates field access in both directions.

**Why TypedDict instead of dataclass?** Exec scripts use JSON at the CLI boundary. TypedDict maps directly to dict access patterns while providing static type safety. No runtime overhead, no serialization decorators, just type checking over the dict operations you're already doing.

## Consumer Pattern: cast() for Type-Aware Access

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, cast() pattern -->

After parsing JSON, use `cast()` to narrow the dict type. This enables autocomplete and type checking for all subsequent field access. Import the TypedDict, parse JSON with `json.loads()`, then `cast()` the result to the TypedDict type. All subsequent key access gets type checking.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, cast() pattern -->

See `trigger_async_learn()` in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` for the full pattern.

## LBYL Guards: Type → Value → Presence

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, filtering pattern -->

When accessing nested fields from JSON, check type before value, value before presence. See the session source filtering in `trigger_async_learn()`:

```python
for source_item in session_sources:
    # 1. Type check: JSON could contain non-dict items
    if not isinstance(source_item, dict):
        continue

    # 2. Value check: For discriminated unions, check discriminator field
    if source_item.get("source_type") != "local":
        continue

    # 3. Presence check: Verify required field exists and has correct type
    session_path = source_item.get("path")
    if not isinstance(session_path, str):
        continue

    # Now safe to use session_path as str
```

**Why this order?** Type guards prevent AttributeError. Value guards (discriminated unions) skip wrong variants. Presence guards catch missing optional fields. Each check narrows the type space before the next check runs.

## Derived vs Schema Fields

**Decision rule**: Session _sources_ come from the schema. Session _types_ (roles) are derived from comparing IDs.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, session type derivation -->

WRONG approach (creating schema fields for derived data):

```python
# DON'T add "session_type": "planning" | "impl" to SessionSourceDict
```

CORRECT approach (derive from relationships):

```python
session_id = source_item.get("session_id")
planning_session_id = sessions["planning_session_id"]
prefix = "planning" if session_id == planning_session_id else "impl"
```

**Why?** The schema describes _where sessions came from_ (local vs remote), not _what role they played_ (planning vs implementation). Session type is a relationship property—comparing a session ID against the known planning session ID. Adding it to the schema would duplicate information already present in the structure.

## Empty Output is Valid, Not an Error

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, empty handling -->

When preprocessing filters out a session (empty, warmup, or other valid reason), treat the empty list as success:

```python
output_paths = _preprocess_session_direct(...)

if not output_paths:
    click.echo("[info] Session filtered (empty/warmup), skipping", err=True)
    continue  # Not an error—this session just didn't need processing
```

**Why?** Filtering is part of normal operation. Warmup sessions and empty sessions are expected cases. Raising an exception would conflate "this session shouldn't be processed" (expected) with "processing failed" (unexpected).

**Debugging requirement**: Always log to stderr when skipping. Silent filtering makes debugging impossible when you're investigating missing data. Include the reason (empty/warmup/wrong type) so future investigators can distinguish intentional filtering from bugs.

## See Also

- `docs/learned/architecture/discriminated-union-error-handling.md` — Pattern for discriminated unions with TypedDict
- `docs/learned/conventions.md` — Frozen dataclass rules, LBYL vs EAFP principles
