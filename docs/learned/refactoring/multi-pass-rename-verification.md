---
title: Multi-Pass Rename Verification
read_when:
  - "completing a libcst-refactor bulk rename"
  - "verifying all old references are gone after a rename"
  - "grepping for old field names after refactoring"
tripwires:
  - action: "verifying a rename by grepping only src/"
    warning: "Grep for old patterns in BOTH src/ AND tests/. Check: constructor params, method params, display strings, test assertions, JSON keys."
  - action: "assuming type checker catches all rename issues"
    warning: "Type checkers miss string literals (JSON keys, display strings, test assertion strings). Always grep after type checking passes."
---

# Multi-Pass Rename Verification

After libcst-refactor completes bulk renames, verify with multiple passes.

## Verification Checklist

- [ ] Grep `src/` for old field/class names
- [ ] Grep `tests/` for old field/class names
- [ ] Check constructor parameter names in `__init__` methods
- [ ] Check method parameter names in definitions
- [ ] Check display strings and user-facing messages
- [ ] Check JSON serialization key names
- [ ] Check test assertion expected values

## Example Commands

```bash
# After renaming issue_number -> plan_id
rg "\.issue_number" src/
rg "issue_number" tests/
rg "\"issue_number\"" tests/  # JSON keys in test assertions
```

## What Type Checking Misses

Even with frozen dataclasses and strict type checking:

- String literals containing field names (`"issue_number"` in JSON tests)
- Docstrings mentioning the field
- Display strings interpolating the field
- Test assertions comparing against expected strings

## Related Documentation

- [Bulk Rename Scope Verification](bulk-rename-scope-verification.md) — verifying only expected files changed
- [Systematic Terminology Renames](systematic-terminology-renames.md) — three-phase rename workflow
