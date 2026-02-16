---
title: CLI Options Validation
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
read_when:
  - "adding new CLI options or flags"
  - "implementing option validation logic"
  - "encountering unvalidated user input"
tripwires:
  - action: "adding new CLI flags without validation"
    warning: "Check if validation logic is needed when adding new flags. Boolean flags rarely need validation, but flags accepting values (paths, names, numbers) should validate constraints."
---

# CLI Options Validation

When adding CLI options, the choice between Click-level validation and runtime validation depends on **where the constraint originates**: external APIs (like Click's built-ins) or domain logic.

## The Core Insight: Two Validation Tiers

Click's type system exists for **API boundaries** — validating that the shape of user input matches what your code expects. Domain constraints (business rules, state dependencies, complex conditions) belong in runtime validation using `Ensure.*` methods.

**Why this matters**: Click validation fails fast at parse time with usage errors. Runtime validation executes in command logic and can provide context-aware error messages with remediation steps.

## Click Validation: Use Click's Built-In Types

For constraints that Click already models, use Click's type system:

| Constraint Type | Click Type                       | Example                                                          |
| --------------- | -------------------------------- | ---------------------------------------------------------------- |
| File must exist | `click.Path(exists=True)`        | `@click.option("--config", type=click.Path(exists=True))`        |
| Choose from set | `click.Choice(["json", "yaml"])` | `@click.option("--format", type=click.Choice(["json", "yaml"]))` |
| Integer range   | `click.IntRange(min=1, max=100)` | `@click.option("--timeout", type=click.IntRange(1, 3600))`       |

<!-- Source: src/erk/cli/commands/land_cmd.py:386 -->

See the `click.prompt()` call with `type=click.IntRange(1, 3)` in `src/erk/cli/commands/land_cmd.py` for a real example validating menu choices.

## Runtime Validation: Use Ensure Methods

For domain constraints that depend on application state or require explanatory error messages:

<!-- Source: src/erk/cli/ensure.py, Ensure class methods -->

Use `Ensure.*` static methods from `src/erk/cli/ensure.py`. These methods:

- Check invariants after parsing (when you have full context)
- Raise `UserFacingCliError` with styled output
- Provide type narrowing (`Ensure.not_none` returns `T` from `T | None`)
- Support custom error messages with remediation steps

**Decision table**:

| Scenario                 | Use This                                          | Rationale                            |
| ------------------------ | ------------------------------------------------- | ------------------------------------ |
| Path must exist          | `click.Path(exists=True)`                         | Click knows about filesystems        |
| String must be non-empty | `Ensure.not_empty(value, "...")`                  | Click has no "non-empty string" type |
| Config field required    | `Ensure.config_field_set(config, "token", "...")` | Depends on loaded config state       |
| Branch must exist        | `Ensure.git_branch_exists(ctx, root, branch)`     | Depends on git state                 |
| Value must be truthy     | `Ensure.truthy(value, "...")`                     | Generic condition check              |

## Anti-Pattern: Don't Validate at Both Layers

<!-- Source: src/erk/cli/commands/pr/address_cmd.py:39-40 -->

**WRONG**: Duplicating validation

```python
@click.option("--dangerous", is_flag=True, required=True)  # Click validation
def command(dangerous: bool) -> None:
    if not dangerous:  # Runtime validation - redundant!
        raise click.UsageError("Missing option '--dangerous'.")
```

This creates two error paths for the same constraint. Pick one layer.

The `address_cmd.py` example validates `--dangerous` at runtime because the validation message includes context about Claude CLI invocation. If the constraint were purely syntactic, Click's `required=True` would suffice.

## What Never Needs Validation

- **Boolean flags**: `--verbose`, `--force` — they're always bool
- **Optional strings without constraints**: `--message` — any string is valid
- **Options with Click defaults**: Click handles missing values

## Error Handling Pattern

Always use `UserFacingCliError` for validation failures. Never use `RuntimeError` or raw `Exception`.

<!-- Source: src/erk/cli/ensure.py:33-53 -->

See `UserFacingCliError` class in `src/erk/cli/ensure.py` — it extends `click.ClickException` so Click catches it at every command level and converts it to styled output with exit code 1.

**Why not RuntimeError**: `RuntimeError` is for code bugs (programmer errors). Validation failures are user errors — they need actionable messages, not stack traces.

## Testing Validation

Test both success and failure paths:

```python
def test_invalid_timeout_rejected():
    """Verify timeout validation rejects zero."""
    result = runner.invoke(command, ["--timeout", "0"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output
```

## Related Documentation

- [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md) - When to use UserFacingCliError vs RuntimeError
- [CLI Development](cli-development.md) - General CLI development patterns
