---
title: Edit Tool Formatting Behavior
read_when:
  - "using the Edit tool to modify Python code"
  - "working with multiline strings in Claude Code"
  - "encountering formatting issues after edits"
  - "running make format after code changes"
tripwires:
  - action: "using Edit tool on Python files with multiline strings"
    warning: "Edit tool preserves exact indentation without auto-formatting. Always run 'make format' after editing Python code with multiline strings."
---

# Edit Tool Formatting Behavior

The Claude Code Edit tool preserves exact indentation and does not auto-format code. This creates a specific pattern when working with Python code that contains multiline strings.

## The Pattern

When using the Edit tool to modify Python code:

1. **Edit preserves indentation**: The tool keeps exactly what you write, including spaces and newlines
2. **Ruff reformats**: Running `make format` (which calls ruff) may reformat multiline strings
3. **CI catches mismatches**: If you don't run format locally, CI will fail

## Why This Matters

Multiline strings in Python are especially sensitive to formatting:

```python
# You write this with Edit tool
message = """
This is a message
with multiple lines
"""

# Ruff may reformat to:
message = """\
This is a message
with multiple lines
"""
```

The Edit tool won't automatically apply ruff's style, so CI will show a diff.

## The Fix

**Always run `make format` after editing Python files:**

```bash
# After using Edit tool on Python files
make format
```

This ensures your local code matches what CI expects.

## When to Run Format

Run `make format` when you've edited:

- Python files with multiline strings (docstrings, heredocs, error messages)
- Python files with complex indentation
- Any Python file if you're unsure

**Safe to skip** if you only edited:

- Single-line changes without strings
- Markdown files (use `make prettier` instead)
- Configuration files (YAML, TOML, JSON)

## Related Workflows

For a complete decision tree on when to run format vs prettier, see [Formatting Workflow](formatting-workflow.md).

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) - Decision tree for format vs prettier
- [CI Tripwires](tripwires.md) - All CI-related tripwires
