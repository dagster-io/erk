---
title: CLI Flag Patterns
read_when:
  - "designing CLI flag requirements"
  - "implementing conditional flag requirements"
  - "documenting flag combinations"
last_audited: "2026-03-05 00:00 PT"
audit_result: edited
---

# CLI Flag Patterns

Patterns for CLI flag design, including asymmetric requirements and flag combinations.

## Asymmetric Flag Requirements

Some flags are only required in certain contexts or combinations. Document these clearly.

### Pattern: Dangerous Mode with Config Default and --safe Override

Commands that invoke Claude with `--dangerously-skip-permissions` use a tri-state resolution pattern:

```python
from erk.cli.ensure import Ensure

@click.command()
@click.option("-d", "--dangerous", is_flag=True, help="Force dangerous mode")
@click.option("--safe", is_flag=True, help="Disable dangerous mode")
@click.pass_obj
def my_command(ctx: ErkContext, *, dangerous: bool, safe: bool) -> None:
    effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)
```

`Ensure.resolve_dangerous()` in `src/erk/cli/ensure.py` resolves the effective dangerous mode:

1. `--dangerous` and `--safe` are mutually exclusive (raises `UsageError`)
2. `--dangerous` → True, `--safe` → False
3. Neither → falls back to `ctx.global_config.live_dangerously` (default: True)

### Pattern: Flag Required in Combination

Some flags become required when others are present:

```python
@click.command()
@click.option("--stream", is_flag=True)
@click.option("--format", type=click.Choice(["json", "text"]))
def my_command(*, stream: bool, format: str | None) -> None:
    # --stream requires --format=json
    if stream and format != "json":
        raise click.UsageError(
            "--stream requires --format=json"
        )
```

## Standard Flag Conventions

### Short Forms

Always provide short forms for common flags:

| Flag          | Short | Pattern                                   |
| ------------- | ----- | ----------------------------------------- |
| `--force`     | `-f`  | `@click.option("-f", "--force", ...)`     |
| `--verbose`   | `-v`  | `@click.option("-v", "--verbose", ...)`   |
| `--quiet`     | `-q`  | `@click.option("-q", "--quiet", ...)`     |
| `--dangerous` | `-d`  | `@click.option("-d", "--dangerous", ...)` |
| `--help`      | `-h`  | Automatic with Click                      |

### Flag Documentation

Include in help text:

1. **What it does** - Primary behavior
2. **When to use** - Common scenarios
3. **How to disable** - If configurable

```python
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Force dangerous mode (skip permission prompts).",
)
@click.option(
    "--safe",
    is_flag=True,
    help="Disable dangerous mode (permission prompts enabled).",
)
```

## Mutual Exclusivity

When flags conflict, enforce at runtime:

```python
@click.command()
@click.option("--json", "output_json", is_flag=True)
@click.option("--quiet", is_flag=True)
def my_command(*, output_json: bool, quiet: bool) -> None:
    if output_json and quiet:
        raise click.UsageError("--json and --quiet are mutually exclusive")
```

Or use Click's built-in:

```python
@click.command()
@click.option("--json", "output_json", is_flag=True, cls=MutuallyExclusiveOption, not_required_if=["quiet"])
@click.option("--quiet", is_flag=True, cls=MutuallyExclusiveOption, not_required_if=["output_json"])
```

## Documenting Flag Requirements

In command docstrings, document asymmetric requirements:

```python
def my_command(...) -> None:
    """Do something potentially destructive.

    Examples:

    \b
      # Basic usage (dangerous by default)
      erk my-command

    \b
      # Run in safe mode (permission prompts enabled)
      erk my-command --safe

    To disable dangerous mode by default:

    \b
      erk config set live_dangerously false
    """
```

## Related Topics

- [Code Conventions](../conventions.md) - Naming and structure standards
- [CLI Output Styling](../cli/output-styling.md) - Output formatting
