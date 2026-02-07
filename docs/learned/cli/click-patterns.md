---
title: Click Patterns
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
    "--codespace",
    type=str,
    default=None,        # None when flag not provided
    is_flag=False,       # Accepts a value
    flag_value="",       # Empty string when flag provided without value
    help="Run in codespace (uses default if name not provided)",
)
```

**Behavior:**

- `erk implement 123` → `codespace=None` (flag not used)
- `erk implement 123 --codespace` → `codespace=""` (use default)
- `erk implement 123 --codespace mybox` → `codespace="mybox"` (use named)

**In code, check for flag usage:**

```python
if codespace is not None:
    # Flag was provided
    codespace_name = codespace if codespace else None  # "" → None for "use default"
```

**Use case:** When you want a flag that can optionally take a value, with a sensible default when no value is given.

## Related Topics

- [Optional Arguments](optional-arguments.md) - Inferring arguments from context
- [Output Styling](output-styling.md) - Formatting CLI output
