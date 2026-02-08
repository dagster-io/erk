---
title: Batch Exec Commands
read_when:
  - implementing batch operations for exec commands
  - designing JSON stdin/stdout interfaces for erk exec
  - understanding batch command success semantics
tripwires:
  - action: "Design batch commands that process items despite validation failures"
    warning: "Validate ALL items upfront before processing ANY items. Stop on first validation error."
    score: 8
  - action: "Use OR semantics for batch success (success=true if any item succeeds)"
    warning: "Use AND semantics: top-level success=true only if ALL items succeed."
    score: 7
  - action: "Return non-zero exit codes for batch command failures"
    warning: "Always exit 0, encode errors in JSON output with per-item success fields."
    score: 6
last_audited: "2026-02-08"
audit_result: clean
---

# Batch Exec Commands

Batch exec commands process multiple items in a single invocation via JSON stdin, providing efficient bulk operations with comprehensive error reporting. They follow a strict contract for input validation, success semantics, and output structure.

## Why Batch Commands Exist

The batch pattern solves three problems:

1. **Startup cost amortization** — Context initialization (loading config, initializing gateways) happens once instead of per-item
2. **Atomic validation** — Reject malformed inputs before any side effects occur
3. **Aggregate reporting** — Single result object showing all successes and failures together

Without batch commands, processing 50 PR threads would require 50 subprocess invocations, each re-initializing the GitHub gateway and parsing `.git/config`. With batch, one invocation handles all 50.

## The Five-Step Contract

Every batch exec command follows this sequence:

1. **Read JSON array from stdin**
2. **Validate ALL items upfront** (fail fast on first validation error)
3. **Process all validated items** (collect per-item results)
4. **Output JSON result** with top-level success and per-item details
5. **Exit 0** (even on errors)

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, resolve_review_threads command -->

Breaking this contract creates ambiguity: callers can't distinguish between "validation failed" and "some items failed" without inspecting the JSON structure.

## Upfront Validation: Why It Matters

The most critical design decision is **validate everything before processing anything**.

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, _validate_batch_input() -->

See `_validate_batch_input()` in `src/erk/cli/commands/exec/scripts/resolve_review_threads.py` for the reference implementation. It returns either `list[ThreadResolutionItem]` or `BatchResolveError`, never mixing the two.

**Why upfront validation prevents problems:**

- **Atomicity** — No partial state mutations when input is malformed
- **Clear feedback** — User sees all validation errors at once, not one at a time through trial-and-error
- **Predictability** — Either all items are processed or none are

**Anti-pattern: Validate-and-process in a single loop**

```python
# WRONG: This processes item 0 even if item 1 is malformed
for item in items:
    if not valid(item):
        return error
    process_item(item)  # Side effect before validation completes!
```

This violates atomicity: if item 5 is malformed, items 0-4 were already processed. The batch is half-executed, but the caller sees an error.

**Correct pattern: Two-phase execution**

```python
# Phase 1: Validate all items, return error or validated list
validated = validate_all(items)
if isinstance(validated, BatchError):
    output_json(validated)
    exit(0)

# Phase 2: Process all validated items
for item in validated:
    process_item(item)  # Now safe: validation passed
```

This guarantees: if you see `results` in the output, validation succeeded and all items were processed.

## Success Semantics: AND Not OR

Top-level `success` field uses **AND semantics**: true only if ALL items succeeded.

```json
{
  "success": true, // ALL items succeeded
  "results": [
    { "thread_id": "PRRT_1", "success": true },
    { "thread_id": "PRRT_2", "success": true }
  ]
}
```

```json
{
  "success": false, // At least ONE item failed
  "results": [
    { "thread_id": "PRRT_1", "success": true },
    { "thread_id": "PRRT_2", "success": false, "error": "..." }
  ]
}
```

**Why AND semantics:**

- **Clear failure detection** — `if result['success']` tells you everything worked
- **No ambiguity** — `success=true` guarantees zero failures
- **Composable** — Scripts can chain batch commands with `&&` based on top-level success

**Anti-pattern: OR semantics** (success=true if ANY item succeeds)

This makes `success` meaningless. Partial failures become indistinguishable from total success without inspecting every result item. Callers must loop through `results` to determine if the batch actually worked, defeating the purpose of a top-level flag.

## Exit Code Convention: Always Zero

Batch commands **always exit 0**, even on errors. All error information lives in JSON output.

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, bottom of resolve_review_threads command -->

**Why always exit 0:**

- **JSON output preserved** — Some shells suppress stdout on non-zero exits
- **Scripting compatibility** — Scripts can use `||` without treating errors as fatal
- **Rich error details** — JSON can encode error types, messages, and per-item context; exit codes cannot

**Exception: Context initialization failures**

If the command can't even initialize context (e.g., not in a git repo), it exits 1. This is acceptable because JSON output is impossible without context.

See the `resolve_review_threads()` command in `src/erk/cli/commands/exec/scripts/resolve_review_threads.py` — it uses `raise SystemExit(0)` in all code paths after stdin is parsed.

## Two Response Shapes

Batch commands return one of two JSON structures, never mixing them:

### Shape 1: Results Array (Validation Passed)

```typescript
{
  "success": boolean,          // AND semantics (all items succeeded)
  "results": [                 // Per-item results
    {
      "success": boolean,      // This item succeeded
      "thread_id": string,     // Item identifier (varies by command)
      // ... item-specific fields
      "error"?: string,        // Present if success=false
      "error_type"?: string    // Machine-readable error category
    }
  ]
}
```

This shape means: validation passed, items were processed, here are the results.

### Shape 2: Top-Level Error (Validation Failed)

```typescript
{
  "success": false,
  "error_type": string,        // e.g. "invalid-input", "invalid-json"
  "message": string            // Human-readable error description
}
```

This shape means: validation failed, no items were processed, no `results` array exists.

**Why two shapes:**

Validation errors are categorically different from processing errors. If input is malformed, there are no "per-item results" to report. The two-shape design makes this distinction explicit.

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, BatchResolveResult and BatchResolveError dataclasses -->

See `BatchResolveResult` and `BatchResolveError` in `src/erk/cli/commands/exec/scripts/resolve_review_threads.py` for the frozen dataclass implementations.

## TypedDict for Input, Dataclass for Output

Input items use `TypedDict` for direct JSON compatibility. Output results use frozen dataclasses with `asdict()` for serialization.

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, ThreadResolutionItem TypedDict -->

**Why TypedDict for input:**

- **No constructor** — `json.loads()` produces dicts, not class instances
- **Validation is explicit** — `_validate_batch_input()` checks types and fields manually
- **Runtime type narrowing** — Cast to `dict[str, Any]` after `isinstance()` check

**Why dataclass for output:**

- **Frozen by default** — Prevents accidental mutation after construction
- **asdict() serialization** — Clean conversion to JSON-serializable dicts
- **Type safety** — Compiler checks field names and types

See `ThreadResolutionItem` (TypedDict) vs `BatchResolveResult` (dataclass) in `src/erk/cli/commands/exec/scripts/resolve_review_threads.py`.

## When to Use Batch vs Single Commands

| Scenario                    | Use Batch | Use Single                 |
| --------------------------- | --------- | -------------------------- |
| Processing 10+ items        | ✅        | ❌ (too slow)              |
| Need atomic validation      | ✅        | ❌ (no upfront validation) |
| Per-item result tracking    | ✅        | ❌ (no aggregate view)     |
| Scripting single operations | ❌        | ✅ (simpler)               |
| Interactive CLI use         | ❌        | ✅ (better UX)             |

**Rule of thumb:** Batch commands are for automation and bulk operations. Single commands are for interactive use and scripts processing one item.

The cutoff is around 5-10 items: below this, the subprocess overhead is negligible. Above this, batch becomes significantly faster.

## Input/Output Examples

### All Items Succeed

**Input (stdin):**

```json
[
  { "thread_id": "PRRT_abc123", "comment": "Fixed via #123" },
  { "thread_id": "PRRT_def456", "comment": "Addressed" },
  { "thread_id": "PRRT_ghi789" }
]
```

**Output (stdout):**

```json
{
  "success": true,
  "results": [
    { "thread_id": "PRRT_abc123", "success": true, "comment_added": true },
    { "thread_id": "PRRT_def456", "success": true, "comment_added": true },
    { "thread_id": "PRRT_ghi789", "success": true, "comment_added": false }
  ]
}
```

### Partial Failure

**Input (stdin):**

```json
[
  { "thread_id": "PRRT_abc123", "comment": "Fixed" },
  { "thread_id": "PRRT_invalid", "comment": "Addressed" },
  { "thread_id": "PRRT_ghi789" }
]
```

**Output (stdout):**

```json
{
  "success": false,
  "results": [
    { "thread_id": "PRRT_abc123", "success": true, "comment_added": true },
    {
      "thread_id": "PRRT_invalid",
      "success": false,
      "error": "Thread not found",
      "error_type": "not_found"
    },
    { "thread_id": "PRRT_ghi789", "success": true, "comment_added": false }
  ]
}
```

Note: `success=false` at top level because one item failed, but processing continued for all items.

### Validation Failure

**Input (stdin):**

```json
[
  { "thread_id": "PRRT_abc123", "comment": "Fixed" },
  { "comment": "Missing thread_id field" },
  { "thread_id": "PRRT_ghi789" }
]
```

**Output (stdout):**

```json
{
  "success": false,
  "error_type": "invalid-input",
  "message": "Item at index 1 missing required 'thread_id' field"
}
```

Note: No `results` array. Validation failed, so no items were processed.

## Related Documentation

- [erk-exec-commands.md](erk-exec-commands.md) — Complete exec command reference
- [exec-script-batch-testing.md](../testing/exec-script-batch-testing.md) — Testing patterns for batch commands
- [exec-script-schema-patterns.md](exec-script-schema-patterns.md) — TypedDict vs dataclass decisions
