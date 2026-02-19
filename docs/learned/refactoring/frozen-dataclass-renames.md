---
title: Frozen Dataclass Field Renames
read_when:
  - "renaming fields on frozen dataclasses"
  - "planning type-safe refactors"
  - "understanding why frozen dataclasses enable confident renames"
tripwires:
  - action: "renaming a frozen dataclass field without updating all constructor call sites"
    warning: "Update: field declarations, constructor kwargs at ALL call sites, internal assignments, docstrings, JSON serialization tests. Missing even one constructor call site causes AttributeError at runtime."
  - action: "trusting type checker alone after frozen dataclass field rename"
    warning: "Type checkers miss test code using **kwargs patterns, JSON serialization tests with string key assertions, docstrings mentioning field names, and display strings interpolating field values."
---

# Frozen Dataclass Field Renames

Frozen dataclasses provide a safety net for mechanical renames, but are not foolproof.

## Why Frozen Helps

With `@dataclass(frozen=True)`:

- Every field access is explicit (`row.plan_id`)
- Type checker catches any missed renames
- No sneaky `setattr` or dictionary access to bypass checks

## The Refactoring Pattern

1. **Rename the field** in the dataclass definition
2. **Run type checker** (ty, mypy, pyright)
3. **Fix every error** — these are the exact locations needing updates
4. **Grep for string references** — type checkers miss these
5. **Trust the type checker** — if it and grep both pass, you found everything

## What Type Checking Misses

Even with frozen dataclasses, grep for:

- String literals containing field names (`"issue_number"` in JSON tests)
- Docstrings mentioning the field
- Display strings interpolating the field
- Test assertions comparing against expected strings

## Update Locations

1. Field declaration in dataclass
2. All `ClassName(field_name=value)` constructor calls
3. Internal `self._field_name = field_name` assignments
4. Docstrings and comments referencing the field
5. Test assertions checking JSON output keys

## Related Documentation

- [Multi-Pass Rename Verification](multi-pass-rename-verification.md) — verification checklist
- [Type-Safe Refactoring](type-safe-refactoring.md) — broader type safety patterns
