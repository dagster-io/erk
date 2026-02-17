---
title: Click Framework Conventions
read_when:
  - "adding Click options to erk CLI commands"
  - "understanding default=None convention in Click options"
  - "distinguishing 'not provided' from 'empty string' in CLI arguments"
tripwires:
  - action: "using a non-None default for an optional Click option"
    warning: "Use default=None to distinguish 'not provided' from 'explicitly set'. This enables three-state semantics (None=omitted, ''=clear, value=set) used throughout erk's CLI."
---

# Click Framework Conventions

Erk's CLI uses Click with specific conventions for option defaults, type handling, and the three-state pattern.

## The `default=None` Convention

<!-- Source: src/erk/cli/commands/pr/submit_cmd.py:77-81 -->
<!-- Source: src/erk/cli/commands/exec/scripts/ (multiple files) -->

Optional Click options use `default=None` to distinguish "not provided" from "explicitly set":

```python
@click.option(
    "--session-id",
    default=None,
    help="Claude session ID for tracing",
)
```

This enables the three-state pattern used by many erk commands:

| Value    | Meaning             | Example CLI        |
| -------- | ------------------- | ------------------ |
| `None`   | Option not provided | (omitted entirely) |
| `""`     | Explicitly cleared  | `--plan ""`        |
| `"#NNN"` | Explicitly set      | `--plan "#6464"`   |

Without `default=None`, Click would set a default value, making it impossible to distinguish "user didn't pass this flag" from "user passed an empty value."

## Type Specification with None Defaults

When combining `default=None` with type constraints:

```python
@click.option("--pr-number", type=int, default=None)
@click.option("--format", type=click.Choice(["json", "text"]), default=None)
```

Click validates the type only when the option is provided. With `default=None`, an unprovided option stays `None` without triggering type validation.

## Related Documentation

- [Command Organization](command-organization.md) — CLI command structure and verb placement
- [Plan Reference Preservation](../objectives/plan-reference-preservation.md) — Three-state pattern in roadmap updates
