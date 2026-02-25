---
title: JSON Parsing Patterns
read_when:
  - "parsing JSON from files or API responses"
  - "validating JSON field presence"
  - "implementing LBYL JSON parsing"
tripwires:
  - action: "using try/except KeyError for JSON field access"
    warning: "Use LBYL pattern: check field presence with `any(f not in data for f in _REQUIRED_FIELDS)` before accessing. Never use try/except for control flow."
    score: 4
---

# JSON Parsing Patterns

Erk uses a consistent LBYL pattern for parsing JSON from external sources (files, API responses). This avoids try/except for control flow.

## Core Pattern: Required Fields Constant + Parse Helper

**Location:** `packages/erk-shared/src/erk_shared/impl_folder.py`

### 1. Define required fields as a module-level constant

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, _REQUIRED_REF_FIELDS -->

A module-level tuple lists every field that must be present. See `_REQUIRED_REF_FIELDS` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

### 2. Check all required fields before accessing any

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, _parse_ref_json -->

The parse helper follows a three-step pattern:

1. Read and decode JSON (the one place `try/except json.JSONDecodeError` is acceptable — corrupted files are genuinely exceptional)
2. LBYL guard: `any(f not in data for f in _REQUIRED_REF_FIELDS)` — validates all required fields exist before accessing any
3. Construct the dataclass from validated fields; optional fields use `.get()` with defaults

See `_parse_ref_json()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

### Key Design Decisions

- **`json.JSONDecodeError` is the one exception**: Invalid JSON is a genuine exceptional case (corrupted file), not a control flow decision. This is acceptable.
- **`any(f not in data for f in ...)` is the guard**: LBYL check that validates all required fields exist before accessing any of them.
- **Return `None` for invalid data**: Callers use LBYL on the return value (`if result is None:`).
- **Optional fields use `.get()` with defaults**: `data.get("labels", [])` — no field presence check needed for optional fields.

## When to Use

- Parsing JSON from files (ref.json, plan-ref.json, issue.json)
- Parsing JSON from API responses
- Any external data source where field presence is not guaranteed

## Anti-Pattern

```python
# WRONG: try/except for field access
def parse_ref(data: dict) -> PlanRef:
    try:
        return PlanRef(
            provider=data["provider"],
            plan_id=data["plan_id"],
            ...
        )
    except KeyError as e:
        raise ValueError(f"Missing field: {e}")
```

This violates the LBYL principle and makes it unclear which field was missing until the exception fires.

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) — LBYL principle
- [Ref JSON Migration](ref-json-migration.md) — Canonical example of this pattern
