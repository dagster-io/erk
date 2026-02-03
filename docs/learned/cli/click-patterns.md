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

## Related Topics

- [Optional Arguments](optional-arguments.md) - Inferring arguments from context
- [Output Styling](output-styling.md) - Formatting CLI output
- [Help Text Formatting](help-text-formatting.md) - Using `\b` for code examples and bulleted lists
