---
title: CI-Aware Commands
read_when:
  - "implementing commands that behave differently in CI"
  - "checking if code is running in GitHub Actions"
  - "skipping user-interactive steps in automated environments"
tripwires:
  - action: "adding user-interactive steps (confirmations, prompts) without CI detection"
    warning: "Commands with user interaction must check `in_github_actions()` and skip prompts in CI. Interactive prompts hang indefinitely in GitHub Actions workflows."
  - action: "using blocking operations (user confirmation, editor launch) in CI-executed code paths"
    warning: "Check `in_github_actions()` before any blocking operation. CI has no terminal for user input."
---

# CI-Aware Commands

Commands that run in both interactive terminals and GitHub Actions CI need special handling. This document explains the CI detection pattern and when to use it.

## The Problem

GitHub Actions workflows run without an interactive terminal. Commands that prompt for user input will hang indefinitely:

- `click.confirm()` - waits for y/n
- `click.prompt()` - waits for text input
- Editor launches (`$EDITOR`) - no terminal to display
- Any code that reads from stdin

## CI Detection Pattern

Use `in_github_actions()` to detect CI environment:

```python
from erk_shared.env import in_github_actions

if in_github_actions():
    # CI-specific behavior (no prompts)
    proceed_automatically()
else:
    # Interactive behavior (prompts allowed)
    if click.confirm("Continue?"):
        proceed_automatically()
```

### Implementation

The detection is simple - it checks the `GITHUB_ACTIONS` environment variable:

```python
def in_github_actions() -> bool:
    """Check if code is running in GitHub Actions CI."""
    return os.environ.get("GITHUB_ACTIONS") == "true"
```

See `erk_shared/env.py` for the canonical implementation.

## When to Use CI Detection

### Use CI Detection For

| Scenario                                    | Interactive         | CI                      |
| ------------------------------------------- | ------------------- | ----------------------- |
| User confirmation before destructive action | `click.confirm()`   | Skip, proceed directly  |
| Progress updates                            | Rich/live display   | Simple print statements |
| Opening URLs in browser                     | `webbrowser.open()` | Print URL instead       |
| Editor launch                               | Launch `$EDITOR`    | Skip or use defaults    |

### Don't Use CI Detection For

- **Business logic**: CI should run the same logic, just without prompts
- **Error handling**: Errors should surface the same way
- **Validation**: Validation should always run

## Real-World Example: /erk:learn

The `/erk:learn` command uses CI detection to skip user confirmation:

````markdown
**CI Detection**: Check if running in CI/streaming mode by running:

```bash
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```
````

**If CI mode (CI_MODE)**: Skip user confirmation. Auto-proceed to write documentation.
**If interactive mode (INTERACTIVE)**: Confirm with user before writing.

````

This allows the learn workflow to complete without hanging in GitHub Actions.

## Common Pitfalls

### Hanging on Confirmation

```python
# WRONG: Will hang in CI
if click.confirm("Delete all files?"):
    delete_files()

# CORRECT: Skip confirmation in CI
if in_github_actions() or click.confirm("Delete all files?"):
    delete_files()
````

### Blocking on Editor

```python
# WRONG: Will hang in CI
subprocess.run(["${EDITOR:-vi}", file_path])

# CORRECT: Skip editor in CI
if not in_github_actions():
    subprocess.run(["${EDITOR:-vi}", file_path])
```

### Rich Console Features

```python
# WRONG: Live display may not work in CI
with Live(table) as live:
    for item in items:
        update_table(table, item)
        live.refresh()

# CORRECT: Use simple output in CI
if in_github_actions():
    for item in items:
        print(f"Processing: {item}")
else:
    with Live(table) as live:
        # ... live display
```

## Testing CI Detection

In tests, mock the environment variable:

```python
def test_ci_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    # Test that command skips confirmation in CI
    result = runner.invoke(cli, ["dangerous-command"])
    assert "Skipping confirmation (CI mode)" in result.output

def test_interactive_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    # Test that command prompts in interactive mode
    result = runner.invoke(cli, ["dangerous-command"], input="y\n")
    assert "Continue?" in result.output
```

## Related Documentation

- [CLI Output Styling](output-styling.md) - Output patterns for CLI commands
- [Erk Architecture Patterns](../architecture/erk-architecture.md) - General architecture patterns
