---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - Writing CLI command docstrings
  - Adding Examples sections to Click commands
  - Formatting bulleted lists in help text
title: Click Help Text Formatting
tripwires:
  - action: "writing Examples sections in CLI docstrings without \b"
    warning:
      "Place \b on its own line after 'Examples:' heading. Without it, Click\
      \ rewraps text and breaks formatting."
  - action: adding bulleted lists to CLI command help text
    warning:
      "Place \b before bulleted/numbered lists to prevent Click from merging\
      \ items into single line."
---

# Click Help Text Formatting

## Why `\b` Exists

Click's help formatter treats consecutive lines as paragraphs and rewraps them to fit terminal width. This behavior makes prose paragraphs responsive to narrow terminals, but it **destroys structural formatting** like code examples, bullet lists, and tables.

The `\b` escape sequence tells Click "stop treating this as paragraph text." Everything after `\b` until the next blank line is preserved character-for-character.

**Without this escape**, bulleted lists collapse into run-on sentences and code examples lose their indentation, making help text unreadable.

## The Rewrapping Problem

Click's paragraph rewrapping optimizes for prose, not structure. When you write:

```
- First item
- Second item
```

Click sees two consecutive lines and joins them: `- First item - Second item`. The structural meaning (separate list items) is lost.

Similarly, code examples with meaningful indentation and line breaks get collapsed into terminal-width chunks, breaking shell copy-paste and visual alignment.

**This is why 72% of erk CLI commands had broken help text** before systematic `\b` adoption (plan #6617 analysis).

## Decision Table: When to Use `\b`

| Content Type                     | Use `\b`? | Why                                           |
| -------------------------------- | --------- | --------------------------------------------- |
| Bulleted lists (`-` or `*`)      | **Yes**   | Items collapse into single line without it    |
| Numbered lists (`1.`)            | **Yes**   | Numbers merge with text across lines          |
| Code examples (shell commands)   | **Yes**   | Indentation and line breaks must be preserved |
| Pre-formatted tables or diagrams | **Yes**   | Column alignment breaks under rewrapping      |
| Normal prose paragraphs          | **No**    | Let Click handle responsive wrapping          |
| Single-line option help          | **No**    | Click formats these correctly automatically   |

## Placement Pattern

`\b` goes on **its own line** immediately before the formatted content:

```python
"""Command description.

Examples:

\b
  # Comment
  erk command --flag value
"""
```

**NOT** on the same line as the heading:

```python
# WRONG
"""
Examples: \b
  erk command
"""
```

The blank line creates a paragraph break; `\b` tells Click not to rewrap the next paragraph.

## Examples Section Standard

<!-- Source: src/erk/cli/commands/doctor.py, doctor_cmd docstring -->
<!-- Source: src/erk/cli/commands/branch/delete_cmd.py, branch_delete docstring -->

See `doctor_cmd()` in `src/erk/cli/commands/doctor.py` for the canonical pattern:

- Heading: `Examples:`
- Blank line
- `\b` on its own line
- Each example indented with 2 spaces
- Shell comments use `#` prefix
- Blank lines between examples for grouping

This format ensures copy-paste works correctly from terminal output.

## Anti-Pattern: Omitting `\b`

**WRONG:**

```python
"""Run diagnostic checks.

Examples:

  # Run checks
  erk doctor

  # Verbose output
  erk doctor --verbose
"""
```

**Rendered output (broken):**

```
Examples: # Run checks erk doctor # Verbose output erk doctor --verbose
```

The examples collapse into an unreadable single line.

**CORRECT:**

```python
"""Run diagnostic checks.

Examples:

\b
  # Run checks
  erk doctor

  # Verbose output
  erk doctor --verbose
"""
```

**Rendered output (preserved):**

```
Examples:

  # Run checks
  erk doctor

  # Verbose output
  erk doctor --verbose
```

## Why Agents Miss This

AI agents trained on Python documentation see standard docstrings without `\b` because most Python code doesn't use Click. When generating CLI help text, agents naturally follow docstring conventions from their training data, omitting the Click-specific escape sequence.

**This is not obvious from reading Click documentation** — the `\b` escape is mentioned briefly in formatting notes but not emphasized as **required for structural content**.

Learned docs exist to capture this kind of cross-cutting knowledge that's easy to miss during implementation.

## Coverage Status

As of plan #6617 (2025 analysis):

- 21 commands (28%) use `\b` correctly
- 53 commands (72%) missing `\b` entirely

**Commands with correct usage span multiple CLI areas:**

- `erk doctor` — diagnostic checks
- `erk launch` — agent session management
- `erk plan log` — planning workflows
- `erk branch delete` — branch operations
- `erk pr summarize` — PR operations
- `erk init capability add/remove` — capability management

**Common mistake pattern:** Commands have Examples sections but no `\b`, causing examples to reflow into single-line output.

## Implementation Checklist

When writing CLI command docstrings:

1. Add `Examples:` heading with blank line after
2. Place `\b` on its own line
3. Indent all examples with 2 spaces
4. Add `\b` before any bulleted/numbered lists
5. Verify: `erk <command> --help | grep -A 10 "Examples:"`

If examples appear on one line in output, `\b` is missing.

## Related Patterns

- For complete Click patterns, see `click-patterns.md`
- For terminal output styling conventions, see `output-styling.md`
