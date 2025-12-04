# Dataclass-Based JSON Schema Documentation for CLI Commands

## Overview

Alternative to PR #2047's TypedDict migration. This plan keeps existing dataclasses and adds automatic JSON output schema documentation to CLI `--help` text via runtime introspection.

## Approach: Runtime Dataclass Introspection

Use Python's built-in `dataclasses.fields()` and `typing.get_type_hints()` to extract schema information at runtime from existing dataclass definitions.

**Key advantages over TypedDict:**
- No migration needed - existing dataclasses stay unchanged
- Single source of truth - schema comes from actual code
- Automatic sync - help text updates when dataclass changes
- Python-native - uses only stdlib modules

## Implementation

### 1. New Module: `schema.py`

Location: `packages/dot-agent-kit/src/dot_agent_kit/cli/schema.py`

**Core functions:**

```python
def format_type(hint) -> str:
    """Convert Python type hint to readable string.

    - bool -> boolean
    - int -> integer
    - str -> string
    - list[str] -> list[string]
    - str | None -> string | null
    - Literal["a", "b"] -> "a" | "b"
    """

def generate_schema(dc_class: type) -> str:
    """Generate schema text from a dataclass using fields() and get_type_hints()."""

def build_epilog(*dataclasses: type) -> str:
    """Combine multiple dataclasses into Click epilog text."""

class SchemaCommand(click.Command):
    """Click Command subclass that preserves newlines in epilog."""
```

### 2. Migration Pattern

**Before:**
```python
@click.command(name="parse-issue-reference")
def parse_issue_reference(issue_reference: str) -> None:
    """Parse GitHub issue reference."""
    ...
```

**After:**
```python
from dot_agent_kit.cli.schema import SchemaCommand, build_epilog

@click.command(
    name="parse-issue-reference",
    cls=SchemaCommand,
    epilog=build_epilog(ParsedIssue, ParseError),
)
def parse_issue_reference(issue_reference: str) -> None:
    """Parse GitHub issue reference."""
    ...
```

### 3. Example Help Output

```
$ dot-agent run erk parse-issue-reference --help
Usage: dot-agent run erk parse-issue-reference [OPTIONS] ISSUE_REFERENCE

  Parse GitHub issue reference from plain number or URL.

Options:
  --help  Show this message and exit.

JSON Output Schema:

Success result with parsed issue number
  success: boolean
  issue_number: integer

Error result when issue reference cannot be parsed
  success: boolean
  error: "invalid_format" | "invalid_number"
  message: string
```

## Files to Create/Modify

### New Files

1. **`packages/dot-agent-kit/src/dot_agent_kit/cli/schema.py`**
   - `format_type()` - type hint formatting
   - `generate_schema()` - dataclass to schema text
   - `build_epilog()` - combine for Click
   - `SchemaCommand` - preserve epilog formatting

2. **`packages/dot-agent-kit/tests/unit/cli/test_schema.py`**
   - Test type formatting (primitives, Optional, Literal, list, dict)
   - Test schema generation
   - Test epilog building
   - Test Click help integration

### Commands to Migrate

All in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/`:

1. `parse_issue_reference.py` - `ParsedIssue`, `ParseError`
2. `find_project_dir.py` - `ProjectInfo`, `ProjectError`
3. `mark_impl_started.py` - `MarkImplSuccess`, `MarkImplError`
4. `post_start_comment.py` - success/error dataclasses
5. `post_pr_comment.py` - success/error dataclasses
6. `get_pr_commit_message.py` - success/error dataclasses
7. `update_dispatch_info.py` - success/error dataclasses

## Implementation Steps

1. Create `schema.py` with core introspection utilities
2. Create test file with comprehensive coverage
3. Migrate `parse_issue_reference.py` as proof of concept
4. Migrate remaining commands

## Type Formatting Rules

| Python Type | Display |
|-------------|---------|
| `bool` | `boolean` |
| `int` | `integer` |
| `float` | `number` |
| `str` | `string` |
| `None` | `null` |
| `list[T]` | `list[T]` |
| `dict[K, V]` | `dict[K, V]` |
| `T \| None` | `T \| null` |
| `Literal["a", "b"]` | `"a" \| "b"` |

## Handling Edge Cases

- **Union types**: Handle both `typing.Union` and Python 3.10+ `|` via `types.UnionType`
- **Nested types**: Recursively format using `get_origin()` and `get_args()`
- **Missing docstrings**: Use class name as fallback title
- **Non-dataclass input**: Raise `TypeError` with clear message