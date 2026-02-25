# Fix: Numeric string fields coerced to int by `_coerce_value`

## Context

Remote plan implementations fail at the post-implementation metadata update step because `_coerce_value()` in `update_plan_header.py` blindly converts all-digit strings to `int`. Fields like `last_remote_impl_run_id` (GitHub Actions run ID `22397458206`) get coerced from `str` → `int`, then `PlanHeaderSchema.validate()` rejects them with `"last_remote_impl_run_id must be a string or null"`. This caused the CI failure on run #22397458206 — the implementation code was written successfully but the metadata update failed, which cascaded into the workflow failing.

Affected fields (string-typed in schema, but receive numeric-only values from CI):
- `last_remote_impl_run_id`
- `last_dispatched_run_id`
- `learn_run_id` (not yet passed from CI, but same pattern)

## Fix 1: Upstream — Make `_coerce_value` field-aware

**File:** `src/erk/cli/commands/exec/scripts/update_plan_header.py`

The `_coerce_value` function currently has no knowledge of which field it's coercing for. Add a set of fields known to be string-typed, and skip int coercion for those.

Change `_parse_fields` to check field names against a known-string-fields set before calling `_coerce_value`:

```python
# Fields that are string-typed in PlanHeaderSchema but often receive
# numeric-only values (e.g. GitHub Actions run IDs).  Never coerce these to int.
_STRING_ONLY_FIELDS: frozenset[str] = frozenset({
    "last_remote_impl_run_id",
    "last_dispatched_run_id",
    "learn_run_id",
})


def _coerce_value(raw: str, *, field_name: str) -> str | None | int:
    if raw == "null":
        return None
    if field_name in _STRING_ONLY_FIELDS:
        return raw
    if raw.lstrip("-").isdigit() and raw != "-":
        return int(raw)
    return raw
```

Update `_parse_fields` to pass `field_name` through:

```python
def _parse_fields(fields: tuple[str, ...]) -> dict[str, str | None | int]:
    for field in fields:
        if "=" not in field:
            msg = f"Invalid field format: '{field}'. Expected key=value."
            raise ValueError(msg)
    return {
        key: _coerce_value(raw_value, field_name=key)
        for field in fields
        for key, raw_value in [field.split("=", 1)]
    }
```

## Fix 2: Defensive — Schema validator coerces int→str with warning

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

For the three affected string-or-null fields, instead of raising `ValueError` when the value is an `int`, coerce it to `str` in-place and emit a `warnings.warn()`. This makes the schema layer resilient to upstream bugs.

For each of these validation blocks (lines ~554-583, ~680-683):
- `last_dispatched_run_id` (line 556)
- `last_remote_impl_run_id` (line 582)
- `learn_run_id` (line 682)

Change from:
```python
if not isinstance(data[FIELD], str):
    raise ValueError("field must be a string or null")
```

To:
```python
if isinstance(data[FIELD], int):
    warnings.warn(
        f"field was int, coercing to str (upstream should pass a string)",
        stacklevel=2,
    )
    data[FIELD] = str(data[FIELD])
elif not isinstance(data[FIELD], str):
    raise ValueError("field must be a string or null")
```

Add `import warnings` at the top of the file.

Note: `data` is a `dict` (constructed via `dict(block.data)` in the caller), so in-place mutation is safe.

## Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`

Add tests for Fix 1:
- `test_run_id_field_stays_string` — passing `last_remote_impl_run_id=22397458206` stores it as `str`, not `int`
- `test_dispatched_run_id_stays_string` — same for `last_dispatched_run_id`
- `test_non_string_field_still_coerced_to_int` — `objective_issue=7823` still becomes `int` (regression guard)

**File:** `tests/shared/github/test_metadata_schemas.py`

Add tests for Fix 2:
- `test_int_run_id_coerced_to_string_with_warning` — passing `int` for `last_remote_impl_run_id` gets coerced, emits warning
- `test_int_dispatched_run_id_coerced_to_string_with_warning` — same for `last_dispatched_run_id`
- `test_int_learn_run_id_coerced_to_string_with_warning` — same for `learn_run_id`

## Files Summary

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/update_plan_header.py` | Add `_STRING_ONLY_FIELDS`, make `_coerce_value` field-aware |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` | Coerce int→str with warning for 3 run ID fields |
| `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py` | Add 3 tests for string-only field behavior |
| `tests/shared/github/test_metadata_schemas.py` | Add 3 tests for defensive coercion with warning |

## Verification

1. Run existing update-plan-header tests: `pytest tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`
2. Run schema tests: `pytest` against the schema test file
3. Run `ruff check` and `ty check` on modified files
