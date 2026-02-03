---
title: Click Help Text Formatting
tripwires:
  - action: "writing Examples sections in CLI docstrings without \b"
    warning: "Place \b on its own line after 'Examples:' heading. Without it, Click rewraps text and breaks formatting."
  - action: "adding bulleted lists to CLI command help text"
    warning: "Place \b before bulleted/numbered lists to prevent Click from merging items into single line."
read_when:
  - "Writing CLI command docstrings"
  - "Adding Examples sections to Click commands"
  - "Formatting bulleted lists in help text"
---

# Click Help Text Formatting

## Overview

Click's default help text formatter rewraps paragraphs, which breaks the formatting of code examples and bulleted lists. The `\b` escape sequence prevents this rewrapping for specific sections.

## The Problem: Paragraph Rewrapping

Click treats consecutive lines as a single paragraph and rewraps them to fit the terminal width. This breaks:

1. **Code examples** - Indentation and line breaks are lost
2. **Bulleted lists** - List items get merged into a single line
3. **Pre-formatted text** - Alignment and structure are destroyed

## The Solution: `\b` Escape Sequence

The `\b` marker tells Click to preserve the following text block's formatting exactly as written, without rewrapping.

**Syntax:**

```python
"""Command description.

\b
  - Bullet point 1
  - Bullet point 2

Examples:

\b
  # Comment
  erk command --flag value

  # Another example
  erk command --other-flag
"""
```

## Before and After Comparison

### Without `\b` (Broken)

```python
@click.command("doctor")
def doctor_cmd(ctx: ErkContext) -> None:
    """Run diagnostic checks on erk setup.

    Checks for:

      - Repository Setup: git config, Claude settings, erk config, hooks
      - User Setup: prerequisites (erk, claude, gt, gh, uv), GitHub auth

    Examples:

      # Run checks (condensed output)
      erk doctor

      # Show all individual checks
      erk doctor --verbose
    """
```

**Rendered output (broken):**

```
Usage: erk doctor [OPTIONS]

Run diagnostic checks on erk setup.

Checks for: - Repository Setup: git config, Claude settings, erk config,
hooks - User Setup: prerequisites (erk, claude, gt, gh, uv), GitHub auth

Examples: # Run checks (condensed output) erk doctor # Show all individual
checks erk doctor --verbose
```

### With `\b` (Correct)

```python
@click.command("doctor")
def doctor_cmd(ctx: ErkContext) -> None:
    """Run diagnostic checks on erk setup.

    Checks for:

    \b
      - Repository Setup: git config, Claude settings, erk config, hooks
      - User Setup: prerequisites (erk, claude, gt, gh, uv), GitHub auth

    Examples:

    \b
      # Run checks (condensed output)
      erk doctor

      # Show all individual checks
      erk doctor --verbose
    """
```

**Rendered output (correct):**

```
Usage: erk doctor [OPTIONS]

Run diagnostic checks on erk setup.

Checks for:

  - Repository Setup: git config, Claude settings, erk config, hooks
  - User Setup: prerequisites (erk, claude, gt, gh, uv), GitHub auth

Examples:

  # Run checks (condensed output)
  erk doctor

  # Show all individual checks
  erk doctor --verbose
```

## When to Use `\b`

**Always use `\b` before:**

1. **Bulleted lists** (`- item` or `* item`)
2. **Numbered lists** (`1. item`)
3. **Code examples** (shell commands, code snippets)
4. **Pre-formatted tables or diagrams**

**Don't use `\b` for:**

- Normal paragraph text (let Click rewrap it naturally)
- Single-line help strings for options

## Pattern: Examples Section

**Standard format for Examples sections:**

```python
"""Command description.

Main explanation paragraph that can wrap.

Examples:

\b
  # Comment describing first example
  erk command --flag value

  # Comment describing second example
  erk command --other-flag

  # Multi-line example
  erk command \\
    --long-flag value \\
    --another-flag
"""
```

**Key characteristics:**

- Blank line before "Examples:"
- `\b` on its own line after "Examples:"
- Each example indented with 2 spaces
- Comments use `#` prefix
- Blank lines between examples for readability

## Real-World Examples

### Command with Bulleted List and Examples

See `src/erk/cli/commands/doctor.py:114-137` for the full docstring. Key pattern: uses `\b` before both the bulleted "Checks for:" list and the "Examples:" section.

### Command with Only Examples

See `src/erk/cli/commands/branch/delete_cmd.py` for a minimal example using `\b` only before the "Examples:" section.

## Coverage Statistics

As of plan #6617 analysis:

- **21 commands** use `\b` correctly (28% of CLI)
- **53 commands** missing `\b` (72% of CLI)

**Commands with correct usage:**

- `erk doctor`
- `erk launch`
- `erk plan log`
- `erk branch delete`
- `erk init capability add`
- `erk init capability remove`
- `erk pr summarize`
- `erk pr address`
- `erk pr fix-conflicts`
- ...and 12 more

**Common pattern in missing commands:** Commands with examples but no `\b`, causing examples to reflow into unreadable single lines.

## Implementation Checklist

When writing a new CLI command:

- [ ] Add "Examples:" section to docstring
- [ ] Place `\b` on its own line after "Examples:"
- [ ] Indent all examples with 2 spaces
- [ ] Add `\b` before any bulleted or numbered lists
- [ ] Test help output: `erk <command> --help`
- [ ] Verify examples are properly formatted

## Testing

**Manual verification:**

```bash
# Check help text rendering
erk doctor --help

# Check for proper formatting
erk doctor --help | grep -A 10 "Examples:"
```

**Expected:** Examples should appear with proper indentation and line breaks preserved.

## Related Documentation

- [Click Patterns](click-patterns.md) - Complete Click usage patterns
- [Output Styling](output-styling.md) - Terminal output formatting
- [CLI Development](../cli/) - Complete CLI development guide
