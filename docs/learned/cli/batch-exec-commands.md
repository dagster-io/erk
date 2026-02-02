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
# CORRECT: Validate all upfront
def validate_all_items(items: list[BatchItem]) -> list[ValidationError] | None:
    errors = []
    for item in items:
        if not item.thread_id.startswith("PRRT_"):
            errors.append({"item": item, "error": "Invalid thread ID"})
    return errors if errors else None

errors = validate_all_items(items)
if errors:
    return {"success": False, "validation_errors": errors}

# Now process all items (validation passed)
for item in items:
    process_item(item)
```

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
- JSON parse errors on stdin (invalid input format)
- Situations where JSON output is impossible

### Output Structure

Standard batch result structure:

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
  ],
  "validation_errors"?: [...], // Present if input validation failed
  "error"?: string,            // Present for catastrophic failures
  "error_type"?: string
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
  "validation_errors": [
    {
      "index": 1,
      "thread_id": "invalid",
      "error": "Thread ID must start with PRRT_"
    }
  ]
}
```

Note: No `results` array on validation failure—items were never processed.

## Data Structures

Common patterns for batch command types:

### BatchResult (Top-Level)

```python
@dataclass(frozen=True)
class BatchResolveResult:
    success: bool
    results: list[ThreadResolutionItem]
```

### Item Result (Per-Item)

```python
# TypedDict for flexibility with optional fields
class ThreadResolutionItem(TypedDict, total=False):
    thread_id: str
    success: bool
    comment_added: bool  # Optional success detail
    error: str           # Present if success=false
    error_type: str      # Machine-readable error
```

**Why TypedDict instead of dataclass:**

- Optional fields without defaults (violates dignified-python for dataclasses)
- Conditional field presence (error only if success=false)
- Direct JSON serialization (no asdict() needed)

### Validation Error

```python
@dataclass(frozen=True)
class BatchValidationError:
    index: int
    item_id: str
    error: str
```

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
