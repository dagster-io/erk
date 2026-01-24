---
title: Type Safety Patterns
read_when:
  - "designing flexible collection types"
  - "working with union types in Python"
  - "handling mixed-type lists"
---

# Type Safety Patterns

Patterns for maintaining type safety with flexible data structures in Python.

## Union Types for Flexible Collections

When a list needs to accept multiple types (e.g., plain strings and Rich `Text` objects), use union types:

```python
from rich.text import Text

def render_table(rows: list[list[str | Text]]) -> None:
    """Render rows that may contain strings or Text objects."""
    for row in rows:
        for cell in row:
            # Both str and Text have __str__, so this works
            print(str(cell))
```

### Benefits

- **Type checker catches errors** - Can't accidentally pass incompatible types
- **Self-documenting** - Signature shows what's accepted
- **IDE support** - Autocomplete works for both types

### When to Use

Use `list[T1 | T2]` when:

- Items share a common interface (both can be stringified)
- Processing logic handles both types uniformly
- The mixed list is intentional (e.g., some items need Rich styling, some don't)

## Type Narrowing

After checking types at runtime, use `isinstance()` to narrow:

```python
def process_cell(cell: str | Text) -> str:
    if isinstance(cell, Text):
        # Type checker knows cell is Text here
        return cell.plain
    # Type checker knows cell is str here
    return cell
```

### assert for Narrowing

When you're confident about the type (e.g., after validation):

```python
def handle_validated_row(row: PlanRowData | None) -> None:
    # We know row is not None after validation
    assert row is not None
    # Type checker now sees row as PlanRowData
    print(row.issue_number)
```

## Duck Typing Alternative

For truly flexible code, use duck typing with Protocol:

```python
from typing import Protocol

class Stringifiable(Protocol):
    def __str__(self) -> str: ...

def render_cell(cell: Stringifiable) -> str:
    return str(cell)
```

### Trade-offs

| Approach   | Pros                   | Cons                         |
| ---------- | ---------------------- | ---------------------------- |
| Union type | Explicit, IDE-friendly | Must list all accepted types |
| Protocol   | Open-ended, extensible | Less obvious what's accepted |
| `Any`      | Maximum flexibility    | No type checking benefit     |

## Avoiding `Any`

Prefer union types or Protocols over `Any`:

```python
# BAD: No type checking
def process(items: list[Any]) -> None: ...

# GOOD: Explicit union
def process(items: list[str | Text | int]) -> None: ...

# GOOD: Protocol for structural typing
def process(items: list[Stringifiable]) -> None: ...
```

## Reference

See `src/erk/tui/widgets/plan_table.py` for union type usage with Rich Text in tables.

## Related Topics

- [Protocol vs ABC Interface Design](protocol-vs-abc.md) - When to use Protocol
- [dignified-python skill](../../.claude/skills/dignified-python) - Project typing standards
