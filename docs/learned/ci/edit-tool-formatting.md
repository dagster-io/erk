---
title: Edit Tool Formatting Behavior
read_when:
  - "using the Edit tool to modify Python code"
  - "encountering formatting issues after edits"
  - "CI failing on formatting checks after using Edit tool"
tripwires:
  - action: "using Edit tool on Python files"
    warning: "Edit tool preserves exact indentation without auto-formatting. Always run 'make format' after editing Python code."
---

# Edit Tool Formatting Behavior

The Claude Code Edit tool preserves literal character-for-character content without applying any formatting rules. This creates a systematic mismatch with CI expectations when editing Python code.

## Why This Matters

**Edit is not format-aware.** When you use the Edit tool to modify Python code, the tool writes exactly what you specify — including indentation, whitespace, and line breaks — without consulting ruff's formatting rules.

**CI expects ruff's style.** The CI pipeline runs `make format` (via ruff) to verify that all Python code matches the project's formatting standard. If your local edits don't match ruff's output, CI fails.

This creates a workflow requirement: you must explicitly run formatting after using Edit, because the tool itself doesn't.

## The Cross-Cutting Pattern

This behavior affects multiple areas:

1. **Multiline strings** — Ruff has specific rules for docstrings, heredocs, and multiline literals that Edit won't apply
2. **Indentation normalization** — Ruff enforces consistent spacing that Edit preserves as-written
3. **Import sorting** — Ruff reorders imports; Edit leaves them as you specify
4. **Trailing whitespace** — Ruff removes it; Edit preserves it

The common failure mode: an agent uses Edit to modify Python code, the code looks correct, but CI fails with formatting diffs.

## Required Workflow

**After every Edit tool invocation on Python files:**

```bash
make format
```

This applies ruff's rules to match what CI expects. Without this step, you're committing pre-formatted code to a post-formatted CI check.

## Decision Heuristic

**Always run format** if you edited:
- Any `.py` file with the Edit tool
- Python files with multiline strings (docstrings, error messages)
- Python files with complex indentation or imports

**Safe to skip** if you:
- Only edited non-Python files (`.md`, `.yaml`, `.toml`)
- Used a different tool that auto-formats (some IDEs)
- Made single-character changes to simple expressions

When in doubt, run `make format`. It's fast and idempotent.

## Why Not Auto-Format in Edit?

Edit tool's literal preservation is intentional: it gives the agent precise control over output. Auto-formatting would introduce ambiguity about whether the tool modified your content.

The trade-off: agents must explicitly invoke formatting as a separate step, which creates the workflow requirement documented here.

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) - Complete decision tree for format vs prettier
- [CI Tripwires](tripwires.md) - All CI-related tripwires
