---
title: DataTable Rich Markup Escaping
read_when:
  - "adding cell values to Textual DataTable"
  - "displaying user data in DataTable cells"
  - "troubleshooting invisible text in DataTable"
tripwires:
  - action: "adding cell values to Textual DataTable"
    warning: "Always wrap in `Text(value)` if strings contain user data with brackets. Otherwise `[anything]` will be interpreted as Rich markup."
---

# DataTable Rich Markup Escaping

Textual's DataTable interprets plain strings as Rich markup by default. This causes user data containing brackets (like `[erk-learn]` prefixes) to disappear.

## The Problem

When you pass a plain string to `DataTable.add_row()`, Rich interprets bracket sequences as markup tags:

```python
# WRONG: The [prefix] disappears because Rich interprets it as markup
table.add_row("[erk-learn] My Plan Title")
# Result: "My Plan Title" (prefix invisible)
```

The `[erk-learn]` text is treated as a Rich style tag. Since no style named `erk-learn` exists, Rich silently renders nothing for that portion.

## The Solution

Wrap cell values in `Text()` objects to escape markup interpretation:

```python
from rich.text import Text

# CORRECT: Text() prevents markup interpretation
table.add_row(Text("[erk-learn] My Plan Title"))
# Result: "[erk-learn] My Plan Title" (fully visible)
```

## When This Matters

Apply `Text()` wrapping when cells may contain:

- **User-provided titles** - May contain `[bracketed]` text
- **Plan prefixes** - `[erk-learn]`, `[erk-plan]`, etc.
- **File paths** - May contain brackets in directory names
- **Technical content** - Code snippets, JSON, type annotations like `list[str]`

## This Is Different from Rich CLI Escaping

For Rich console output (not DataTable), use `escape_markup()`:

```python
from rich.markup import escape as escape_markup

# For console.print() or Label with markup=True
console.print(f"Title: {escape_markup(user_title)}")
```

DataTable cells require `Text()` wrapping, not `escape_markup()`. The `Text()` approach disables markup parsing entirely for that cell, while `escape_markup()` escapes special characters but still allows markup in other parts of the string.

## Pattern for TUI Plan Tables

When populating a plan table with titles that may have prefixes:

```python
from rich.text import Text

def populate(self, plans: list[PlanRowData]) -> None:
    for plan in plans:
        self.add_row(
            plan.issue_number,
            Text(plan.title),  # Wrap to prevent [prefix] interpretation
            plan.pr_display,
            # ...
        )
```

## Related Topics

- [Textual API Quirks](quirks.md) - Other Textual gotchas including URL quoting in link tags
- [TUI Architecture](../tui/architecture.md) - Data flow through the TUI
- [CLI Output Styling Guide](../cli/output-styling.md) - CLI-specific Rich markup escaping using `escape_markup()`
