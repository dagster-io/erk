---
title: GitHub URL Parsing Architecture
read_when:
  - "parsing GitHub URLs"
  - "extracting PR or issue numbers from URLs"
  - "understanding github parsing layers"
---

# GitHub URL Parsing Architecture

This document describes the two-layer architecture for parsing GitHub URLs and extracting identifiers (PR numbers, issue numbers, repo names).

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              CLI Layer                       │
│   erk.cli.github_parsing                     │
│   - Raises SystemExit on failure             │
│   - User-friendly error messages             │
│   - CLI-specific formatting                  │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│            Pure Parsing Layer                │
│   erk_shared.github.parsing                  │
│   - Returns int | None                       │
│   - No side effects                          │
│   - Reusable across contexts                 │
└─────────────────────────────────────────────┘
```

## Layer 1: Pure Parsing (`erk_shared.github.parsing`)

The foundational layer provides pure parsing functions:

```python
from erk_shared.github.parsing import (
    parse_pr_number,
    parse_issue_number,
    parse_repo_from_url,
)

# Returns int | None - no exceptions
pr_number = parse_pr_number("https://github.com/owner/repo/pull/123")
# Returns: 123

issue_number = parse_issue_number("https://github.com/owner/repo/issues/456")
# Returns: 456

# Invalid input returns None
result = parse_pr_number("not-a-url")
# Returns: None
```

**Characteristics:**

- Returns `int | None` (never raises)
- No dependencies on CLI frameworks
- Pure functions with no side effects
- Can be used in libraries, tests, scripts

## Layer 2: CLI Wrappers (`erk.cli.github_parsing`)

The CLI layer wraps pure functions with user-friendly error handling:

```python
from erk.cli.github_parsing import (
    require_pr_number,
    require_issue_number,
)

# Raises SystemExit with message on failure
pr_number = require_pr_number("invalid-url")
# Exits with: "Error: Could not parse PR number from 'invalid-url'"

# On success, returns the parsed value
pr_number = require_pr_number("https://github.com/owner/repo/pull/123")
# Returns: 123
```

**Characteristics:**

- Raises `SystemExit` on invalid input
- Provides user-friendly error messages
- Uses click.echo for output formatting
- Only used in CLI command implementations

## Canonical Import Locations

| Function               | Import From                 | Returns        |
| ---------------------- | --------------------------- | -------------- |
| `parse_pr_number`      | `erk_shared.github.parsing` | `int \| None`  |
| `parse_issue_number`   | `erk_shared.github.parsing` | `int \| None`  |
| `parse_repo_from_url`  | `erk_shared.github.parsing` | `str \| None`  |
| `require_pr_number`    | `erk.cli.github_parsing`    | `int` or exits |
| `require_issue_number` | `erk.cli.github_parsing`    | `int` or exits |

## Usage Guidelines

### In CLI Commands

Use the `require_*` functions from CLI layer:

```python
# In src/erk/cli/commands/pr.py
from erk.cli.github_parsing import require_pr_number

@click.command()
@click.argument("url_or_number")
def show_pr(url_or_number: str) -> None:
    pr_number = require_pr_number(url_or_number)
    # If we get here, pr_number is valid int
    click.echo(f"PR #{pr_number}")
```

### In Libraries and Business Logic

Use the pure parsing functions:

```python
# In src/erk_shared/services/pr_service.py
from erk_shared.github.parsing import parse_pr_number

def process_pr(url_or_number: str) -> Result:
    pr_number = parse_pr_number(url_or_number)
    if pr_number is None:
        return Result.error("Invalid PR reference")
    return Result.success(pr_number)
```

### In Tests

Use pure functions for predictable testing:

```python
from erk_shared.github.parsing import parse_pr_number

def test_parse_pr_number_from_url():
    result = parse_pr_number("https://github.com/owner/repo/pull/42")
    assert result == 42

def test_parse_pr_number_invalid():
    result = parse_pr_number("not-a-url")
    assert result is None
```

## Anti-Patterns

### Don't: Create Local Helper Functions

```python
# BAD - don't duplicate parsing logic
def _extract_pr_number(url: str) -> int | None:
    match = re.search(r"/pull/(\d+)", url)
    return int(match.group(1)) if match else None
```

Use the shared module instead.

### Don't: Re-export from Other Modules

```python
# BAD - don't re-export
from erk_shared.github.parsing import parse_pr_number
__all__ = ["parse_pr_number"]  # Re-exporting
```

Import directly from the canonical location.

### Don't: Mix Layers

```python
# BAD - using CLI layer in library code
from erk.cli.github_parsing import require_pr_number

def library_function(url: str) -> int:
    return require_pr_number(url)  # Will call SystemExit!
```

Use pure layer in library code.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - Similar two-layer pattern for subprocess calls
- [Protocol vs ABC](protocol-vs-abc.md) - Interface design patterns
