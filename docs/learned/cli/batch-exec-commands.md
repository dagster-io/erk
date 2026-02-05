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
last_audited: "2026-02-05 14:25 PT"
audit_result: edited
---

# Batch Exec Commands

Batch exec commands process multiple items in a single invocation via JSON stdin, providing efficient bulk operations with comprehensive error reporting. They follow a strict contract for input validation, success semantics, and output structure.

## Pattern Overview

A batch exec command:

1. **Reads JSON array from stdin** (list of items to process)
2. **Validates ALL items upfront** before processing ANY
3. **Processes all items** (or fails fast on validation error)
4. **Outputs JSON result with per-item success** to stdout
5. **Always exits 0** (even on errors)

## Design Contract

### Input Validation

**CRITICAL**: Validate the entire input array before processing any items.

```python
# CORRECT: Validate all upfront, return error or validated items
def validate_batch_input(data: object) -> list[ValidatedItem] | BatchError:
    if not isinstance(data, list):
        return BatchError(success=False, error_type="invalid-input", message="...")
    validated = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict) or "required_field" not in item:
            return BatchError(success=False, error_type="invalid-input", message=f"Item {idx} invalid")
        validated.append(item)
    return validated

validated = validate_batch_input(data)
if isinstance(validated, BatchError):
    output_json(validated)
    raise SystemExit(0)

# Now process all items (validation passed)
for item in validated:
    process_item(item)
```

See `_validate_batch_input()` in `resolve_review_threads.py` for the concrete implementation.

**WRONG: Process during validation**

```python
# This violates atomicity - some items processed before validation completes
for item in items:
    if not validate(item):
        return error
    process_item(item)  # Half the batch might be processed!
```

**Why upfront validation matters:**

- **Atomicity**: Don't partially modify state before discovering validation errors
- **Clear feedback**: User sees all validation errors at once, not one at a time
- **Predictability**: Either all items are processed or none are

### Success Semantics: AND (Not OR)

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

- **Clear failure detection**: `if result['success']` tells you everything worked
- **No ambiguity**: success=true guarantees zero failures
- **Composable**: Scripts can chain batch commands with `&&`

**Anti-pattern: OR semantics** (success=true if ANY item succeeds)

This makes `success` meaningless: partial failures are indistinguishable from total success without inspecting every result item.

### Exit Code Convention

**Always exit 0**, even on errors. Encode all error information in JSON output.

```python
# CORRECT
try:
    result = process_batch(items)
    print(json.dumps(result))
    sys.exit(0)  # Always 0
except Exception as e:
    error_result = {"success": False, "error": str(e)}
    print(json.dumps(error_result))
    sys.exit(0)  # Still 0
```

**Why always exit 0:**

- **JSON output preserved**: Non-zero exits might suppress stdout in some shells
- **Scripting compatibility**: Scripts can use `||` without treating errors as fatal
- **Error details in JSON**: Richer error information than exit codes alone

**When to use non-zero exits:**

- Context initialization failures (can't even load config)
- Situations where JSON output is impossible

Note: JSON parse errors on stdin still exit 0 with an error JSON response (see `resolve_review_threads.py` for the pattern).

### Output Structure

Standard batch result structure (two response shapes):

**Success/partial failure** (validation passed, items were processed):

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

**Validation/parse error** (items were never processed):

```typescript
{
  "success": false,
  "error_type": string,        // e.g. "invalid-input", "invalid-json"
  "message": string            // Human-readable error description
}
```

## When to Use Batch vs Single Commands

| Scenario                    | Use Batch | Use Single                 |
| --------------------------- | --------- | -------------------------- |
| Processing 10+ items        | ✅        | ❌ (too slow)              |
| Need atomic validation      | ✅        | ❌ (no upfront validation) |
| Per-item result tracking    | ✅        | ❌ (no aggregate view)     |
| Scripting single operations | ❌        | ✅ (simpler)               |
| Interactive CLI use         | ❌        | ✅ (better UX)             |

**Rule of thumb**: Batch commands are for automation and bulk operations. Single commands are for interactive use and scripts processing one item.

## Example: resolve-review-threads Batch Command

The `resolve-review-threads` command demonstrates the pattern.

### Input (stdin)

```json
[
  { "thread_id": "PRRT_abc123", "comment": "Fixed via #123" },
  { "thread_id": "PRRT_def456", "comment": "Addressed" },
  { "thread_id": "PRRT_ghi789" }
]
```

### Output (stdout) - All Success

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

### Output - Partial Failure

```json
{
  "success": false,
  "results": [
    { "thread_id": "PRRT_abc123", "success": true, "comment_added": true },
    {
      "thread_id": "PRRT_def456",
      "success": false,
      "error": "Thread not found",
      "error_type": "not_found"
    },
    { "thread_id": "PRRT_ghi789", "success": true, "comment_added": false }
  ]
}
```

### Output - Validation Failure

```json
{
  "success": false,
  "error_type": "invalid-input",
  "message": "Item at index 1 missing required 'thread_id' field"
}
```

Note: No `results` array on validation failure -- the response uses `BatchResolveError` shape with `error_type` and `message` instead.

## Data Structures

See the reference implementation in `src/erk/cli/commands/exec/scripts/resolve_review_threads.py` for concrete types:

- **`BatchResolveResult`** (frozen dataclass): Top-level result with `success: bool` and `results: list[dict[str, object]]`
- **`BatchResolveError`** (frozen dataclass): Error response with `success: bool`, `error_type: str`, `message: str`
- **`ThreadResolutionItem`** (TypedDict): Input item schema with `thread_id: str` and `comment: str | None`

Per-item output results use `ResolveThreadSuccess` / `ResolveThreadError` from `resolve_review_thread.py`, serialized to dicts via `asdict()`.

**Design note:** Input items use `TypedDict` for direct JSON compatibility. Output results use frozen dataclasses with `asdict()` for serialization. Validation errors use the same `BatchResolveError` dataclass as other error responses.

## Testing Batch Commands

See [exec-script-batch-testing.md](../testing/exec-script-batch-testing.md) for test organization patterns:

- Success cases (all items succeed)
- Partial failure (mixed success/error results)
- Validation errors (upfront rejection)
- JSON structure verification

## Related Documentation

- [erk-exec-commands.md](erk-exec-commands.md) - Complete exec command reference
- [exec-script-batch-testing.md](../testing/exec-script-batch-testing.md) - Testing patterns for batch commands
- [exec-script-schema-patterns.md](exec-script-schema-patterns.md) - TypedDict vs dataclass decisions
