---
title: GitHub URL Parsing Architecture
read_when:
  - "parsing GitHub URLs"
  - "extracting PR or issue numbers from URLs"
  - "understanding github parsing layers"
last_audited: "2026-02-04 20:22 PT"
audit_result: edited
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
│   erk_shared.gateway.github.parsing                  │
│   - Returns int | None                       │
│   - No side effects                          │
│   - Reusable across contexts                 │
└─────────────────────────────────────────────┘
```

## Layer 1: Pure Parsing (`erk_shared.gateway.github.parsing`)

The foundational layer provides pure parsing functions:

```python
from erk_shared.gateway.github.parsing import (
    parse_pr_number_from_url,
    parse_issue_number_from_url,
    extract_owner_repo_from_github_url,
)

# Returns int | None - no exceptions
pr_number = parse_pr_number_from_url("https://github.com/owner/repo/pull/123")
# Returns: 123

issue_number = parse_issue_number_from_url("https://github.com/owner/repo/issues/456")
# Returns: 456

# Invalid input returns None
result = parse_pr_number_from_url("not-a-url")
# Returns: None
```

**Characteristics:**

- Returns `int | None` (never raises)
- No dependencies on CLI frameworks
- Pure functions with no side effects
- Can be used in libraries, tests, scripts

## Layer 2: CLI Wrappers (`erk.cli.github_parsing`)

The CLI layer provides identifier parsing with user-friendly error handling:

```python
from erk.cli.github_parsing import (
    parse_pr_identifier,
    parse_issue_identifier,
)

# Raises SystemExit with message on failure
pr_number = parse_pr_identifier("invalid-input")
# Exits with formatted error message showing expected formats

# On success, returns the parsed value
pr_number = parse_pr_identifier("123")  # Plain number
# Returns: 123
pr_number = parse_pr_identifier("https://github.com/owner/repo/pull/123")  # URL
# Returns: 123
```

**Characteristics:**

- Raises `SystemExit` on invalid input
- Provides user-friendly error messages
- Uses click.echo for output formatting
- Only used in CLI command implementations

### Extended Identifier Parsing

For commands that need to accept user-friendly identifiers beyond URLs, use the `parse_*_identifier` functions:

```python
from erk.cli.github_parsing import (
    parse_issue_identifier,
    parse_pr_identifier,
)

# parse_issue_identifier handles three formats:
issue_num = parse_issue_identifier("123")       # Plain number -> 123
issue_num = parse_issue_identifier("P456")      # P-prefixed -> 456
issue_num = parse_issue_identifier("p789")      # Case-insensitive -> 789
issue_num = parse_issue_identifier("https://github.com/owner/repo/issues/42")  # URL -> 42

# parse_pr_identifier handles two formats:
pr_num = parse_pr_identifier("123")             # Plain number -> 123
pr_num = parse_pr_identifier("https://github.com/owner/repo/pull/42")  # URL -> 42
```

**When to use:**

- `parse_issue_identifier`: Plan-related commands (`erk plan co`, `erk plan view`, etc.) where users may use P-prefixed IDs
- `parse_pr_identifier`: PR-related commands that accept PR numbers or URLs
- Layer 1 functions (`parse_pr_number_from_url`, `parse_issue_number_from_url`): When you only need URL parsing in non-CLI contexts

## Canonical Import Locations

| Function                             | Import From                         | Returns                   |
| ------------------------------------ | ----------------------------------- | ------------------------- |
| `parse_pr_number_from_url`           | `erk_shared.gateway.github.parsing` | `int \| None`             |
| `parse_issue_number_from_url`        | `erk_shared.gateway.github.parsing` | `int \| None`             |
| `extract_owner_repo_from_github_url` | `erk_shared.gateway.github.parsing` | `tuple[str, str] \| None` |
| `parse_issue_identifier`             | `erk.cli.github_parsing`            | `int` or exits            |
| `parse_pr_identifier`                | `erk.cli.github_parsing`            | `int` or exits            |

## Usage Guidelines

### In CLI Commands

Use the `parse_*_identifier` functions from CLI layer:

```python
# In src/erk/cli/commands/pr.py
from erk.cli.github_parsing import parse_pr_identifier

@click.command()
@click.argument("url_or_number")
def show_pr(url_or_number: str) -> None:
    pr_number = parse_pr_identifier(url_or_number)
    # If we get here, pr_number is valid int
    click.echo(f"PR #{pr_number}")
```

### In Libraries and Business Logic

Use the pure parsing functions:

```python
# In src/erk_shared/services/pr_service.py
from erk_shared.gateway.github.parsing import parse_pr_number_from_url

def process_pr(url: str) -> Result:
    pr_number = parse_pr_number_from_url(url)
    if pr_number is None:
        return Result.error("Invalid PR URL")
    return Result.success(pr_number)
```

### In Tests

Use pure functions for predictable testing:

```python
from erk_shared.gateway.github.parsing import parse_pr_number_from_url

def test_parse_pr_number_from_url():
    result = parse_pr_number_from_url("https://github.com/owner/repo/pull/42")
    assert result == 42

def test_parse_pr_number_invalid():
    result = parse_pr_number_from_url("not-a-url")
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
from erk_shared.gateway.github.parsing import parse_pr_number_from_url
__all__ = ["parse_pr_number_from_url"]  # Re-exporting
```

Import directly from the canonical location.

### Don't: Mix Layers

```python
# BAD - using CLI layer in library code
from erk.cli.github_parsing import parse_pr_identifier

def library_function(url: str) -> int:
    return parse_pr_identifier(url)  # Will call SystemExit!
```

Use pure layer in library code.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - Similar two-layer pattern for subprocess calls
- [Protocol vs ABC](protocol-vs-abc.md) - Interface design patterns
