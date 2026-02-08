---
title: Click Help Text Formatting
last_audited: "2026-02-08 13:57 PT"
audit_result: edited
content_type: reference_cache
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

## Before and After Comparison

This section demonstrates the full impact of Click's rewrapping on a real command docstring. Click's `\b` behavior is underdocumented -- the escape is mentioned briefly in Click's formatting notes but not emphasized as **required for structural content**.

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

Both the bulleted list and the examples section are collapsed into run-on text. The list items lose their structure, and shell commands become impossible to copy-paste.

### With `\b` (Correct)

<!-- Source: src/erk/cli/commands/doctor.py, doctor_cmd docstring -->

See the `doctor_cmd()` docstring in `src/erk/cli/commands/doctor.py` for the canonical example. It places `\b` on its own line before both the bulleted "Checks for" list and the "Examples:" section. The rendered `--help` output preserves every structural element: list items on separate lines, indentation intact, shell commands on their own lines.

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

See also `branch_delete()` in `src/erk/cli/commands/branch/delete_cmd.py` for another example of the same pattern applied to numbered lists.

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

**This is not obvious from reading Click documentation** -- the `\b` escape is mentioned briefly in formatting notes but not emphasized as **required for structural content**.

Learned docs exist to capture this kind of cross-cutting knowledge that's easy to miss during implementation.

## Coverage Status

Adoption has improved since plan #6617 (2025 analysis) but many commands still lack `\b`. To check current counts, search for `\\b` in CLI command docstrings under `src/erk/cli/commands/`.

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
