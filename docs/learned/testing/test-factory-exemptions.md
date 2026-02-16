---
description: Test factory functions are exempt from production code rules
read_when:
  - bot flags default in make_* or create_* function
  - applying coding standards to test helpers
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Test Factory Function Exemptions

## The Rule

Test factory functions (functions whose purpose is creating test data with sensible defaults) are exempt from the "no default parameter values" rule.

## Identification

Functions named `make_*` or `create_*` in test code that exist to provide convenient test data creation.

## Example

<!-- Source: tests/unit/tui/providers/test_provider.py, make_plan_row -->

See `make_plan_row()` in `tests/unit/tui/providers/test_provider.py` - uses defaults for all parameters. This is intentional design for test ergonomics.

## When Bots Flag

If dignified-code-simplifier flags a default in a test factory:

1. Check if function is named `make_*` or `create_*`
2. Check if nearby parameters also use defaults
3. If yes: resolve as false positive, test factories use defaults by design
