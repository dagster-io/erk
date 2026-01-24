---
title: CLI Flag Patterns
read_when:
  - "designing CLI flag requirements"
  - "implementing conditional flag requirements"
  - "documenting flag combinations"
---

# CLI Flag Patterns

Patterns for CLI flag design, including asymmetric requirements and flag combinations.

## Asymmetric Flag Requirements

Some flags are only required in certain contexts or combinations. Document these clearly.

### Pattern: Flag Required Unless Config Disables

The `--dangerous` flag is required by default but can be disabled via config:

```python
@click.command()
@click.option("-d", "--dangerous", is_flag=True)
@click.pass_obj
def my_command(ctx: ErkContext, *, dangerous: bool) -> None:
    # Require --dangerous unless config disables requirement
    if not dangerous:
        require_flag = (
            ctx.global_config is None
            or ctx.global_config.require_dangerous_flag
        )
        if require_flag:
            raise click.UsageError(
                "Missing option '--dangerous'.\n"
                "To disable: erk config set require_dangerous_flag false"
            )
```

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
    help="Acknowledge that this command may modify files. "
         "To disable: erk config set require_dangerous_flag false",
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
      # Basic usage (requires --dangerous)
      erk my-command --dangerous

    To disable the --dangerous flag requirement:

    \b
      erk config set require_dangerous_flag false
    """
```

## Related Topics

- [Code Conventions](../conventions.md) - Naming and structure standards
- [CLI Output Styling](../cli/output-styling.md) - Output formatting
