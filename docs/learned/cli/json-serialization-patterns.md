---
title: JSON Serialization Patterns for Exec Commands
read_when:
  - "implementing erk exec commands with JSON output"
  - "serializing dataclasses to JSON"
  - "handling datetime or tuple fields in JSON output"
  - "working with --format json option"
---

# JSON Serialization Patterns for Exec Commands

When implementing `erk exec` commands that output JSON, handle non-JSON-native types (datetime, tuple) with pure helper functions that convert to JSON-compatible types.

## The Pattern

Use a pure helper function `_serialize_<type>()` to convert dataclass instances to JSON-compatible dictionaries:

```python
def _serialize_plan_row(row: PlanRowData) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict.

    Handles datetime fields (to ISO 8601 strings) and tuple fields
    (log_entries) to lists for JSON compatibility.
    """
    data = dataclasses.asdict(row)

    # Convert datetime to ISO 8601 string
    for key in ("last_local_impl_at", "last_remote_impl_at"):
        if isinstance(data[key], datetime):
            data[key] = data[key].isoformat()

    # Convert tuple of tuples to list of lists
    data["log_entries"] = [list(entry) for entry in row.log_entries]

    return data
```

## Type-Specific Conversion Rules

### Datetime → ISO 8601 String

```python
# Convert datetime to string
if isinstance(data[key], datetime):
    data[key] = data[key].isoformat()

# Output: "2025-01-15T10:30:00"
```

**Why**: JSON has no native datetime type. ISO 8601 is the standard format.

### Tuple → List

```python
# Convert single tuple to list
data["labels"] = list(row.labels)

# Convert tuple of tuples to list of lists
data["log_entries"] = [list(entry) for entry in row.log_entries]
```

**Why**: JSON has no tuple type, only arrays (lists in Python).

### Dataclass → Dict

```python
# Start with dataclasses.asdict()
data = dataclasses.asdict(row)

# Then convert specific fields
data["created_at"] = data["created_at"].isoformat()
```

**Why**: `dataclasses.asdict()` handles nested dataclasses but doesn't convert datetime/tuple.

## Pure Helper Function Properties

The serialization helper should be:

1. **Pure function**: No side effects, no I/O
2. **Single responsibility**: Only converts types, doesn't fetch data
3. **Testable**: Easy to test with fake data
4. **Named with underscore prefix**: `_serialize_*` indicates internal helper

```python
# ✅ GOOD: Pure helper
def _serialize_plan_row(row: PlanRowData) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict."""
    data = dataclasses.asdict(row)
    # ... conversions ...
    return data

# ❌ BAD: Mixed concerns
def serialize_plan_row(row: PlanRowData, provider: PlanDataProvider) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict."""
    data = dataclasses.asdict(row)
    data["extra_info"] = provider.fetch_extra_info(row.id)  # I/O in serializer
    return data
```

## Usage in Command

Call the helper when outputting JSON:

```python
@click.command(name="dash-data")
@click.pass_context
def dash_data(ctx: click.Context, ...) -> None:
    """Serialize plan dashboard data to JSON."""
    # ... fetch data ...

    rows = provider.fetch_plans(filters)

    # Serialize each row
    serialized = [_serialize_plan_row(row) for row in rows]

    # Output JSON
    output = {"success": True, "plans": serialized, "count": len(serialized)}
    click.echo(json.dumps(output, indent=2))
```

## Reference Implementation

See `src/erk/cli/commands/exec/scripts/dash_data.py` for a complete example:

- `_serialize_plan_row()` helper at line 34
- Handles datetime → `.isoformat()`
- Handles tuple of tuples → list of lists
- Used in main command to serialize plan data

## Common Mistakes

### Using json.dumps() Directly Without Conversion

```python
# ❌ BAD: Will fail on datetime
click.echo(json.dumps(dataclasses.asdict(row)))

# ✅ GOOD: Convert first
click.echo(json.dumps(_serialize_row(row)))
```

### Converting Too Early

```python
# ❌ BAD: Converting before you need to
serialized = _serialize_plan_row(row)
filtered = filter_plans(serialized)  # Working with dict, not dataclass

# ✅ GOOD: Work with dataclass, convert at the end
filtered = filter_plans(row)
serialized = _serialize_plan_row(filtered)
```

## Testing

Test the serialization helper independently:

```python
def test_serialize_plan_row_converts_datetime():
    """Verify datetime fields converted to ISO 8601."""
    row = PlanRowData(
        issue_number=123,
        title="Test",
        last_local_impl_at=datetime(2025, 1, 15, 10, 30),
        ...
    )

    result = _serialize_plan_row(row)

    assert result["last_local_impl_at"] == "2025-01-15T10:30:00"
    assert isinstance(result["last_local_impl_at"], str)
```

## Related Documentation

- [erk exec Commands](erk-exec-commands.md) - General exec command patterns
- [Exec Command Patterns](exec-command-patterns.md) - Output formatting patterns
