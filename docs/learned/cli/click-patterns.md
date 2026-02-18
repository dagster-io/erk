---
title: Click Patterns
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
read_when:
  - "implementing CLI options with complex behavior"
  - "creating flags that optionally accept values"
  - "designing CLI flags with default behaviors"
---

# Click Patterns

Advanced patterns for Click option and flag behavior.

## Optional Value Flags with Defaults

Use `is_flag=False` with `flag_value` to create flags that work both with and without values:

```python
@click.option(
    "--environment",
    type=str,
    default=None,        # None when flag not provided
    is_flag=False,       # Accepts a value
    flag_value="",       # Empty string when flag provided without value
    help="Use environment (uses default if name not provided)",
)
```

**Behavior:**

- `erk command` → `environment=None` (flag not used)
- `erk command --environment` → `environment=""` (use default)
- `erk command --environment staging` → `environment="staging"` (use named)

**In code, check for flag usage:**

```python
if environment is not None:
    # Flag was provided
    env_name = environment if environment else None  # "" → None for "use default"
```

**Use case:** When you want a flag that can optionally take a value, with a sensible default when no value is given.

## Omit Click Default Parameters

Click options have implicit defaults: `required=False` and `default=None`. Omit these from decorators — they add noise without changing behavior.

<!-- Source: src/erk/cli/commands/exec/scripts/update_objective_node.py:313-320 -->

```python
# WRONG - redundant defaults
@click.option(
    "--status",
    "explicit_status",
    required=False,       # This is Click's default
    default=None,         # This is Click's default
    type=click.Choice(["done", "pending"]),
    help="Status to set",
)

# CORRECT - omit defaults
@click.option(
    "--status",
    "explicit_status",
    type=click.Choice(["done", "pending"]),
    help="Status to set",
)
```

**When to keep `required`**: Only include `required=True` — the non-default case.

**When to keep `default`**: Only when setting a non-None default value (e.g., `default="text"`).

## IntRange Updates for Menu Options

When adding new choices to an interactive menu that uses `click.IntRange`, update the range bounds to include the new option:

```python
# Before: 3 menu options
@click.option("--choice", type=click.IntRange(1, 3))

# After: added 4th option
@click.option("--choice", type=click.IntRange(1, 4))
```

Forgetting to update the range causes the new option to be rejected at the CLI validation layer.

## Related Topics

- [Optional Arguments](optional-arguments.md) - Inferring arguments from context
- [Output Styling](output-styling.md) - Formatting CLI output
- [Help Text Formatting](help-text-formatting.md) - Using `\b` for code examples and bulleted lists
