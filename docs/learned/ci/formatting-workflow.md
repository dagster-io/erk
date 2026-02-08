---
title: Formatting Workflow Decision Tree
read_when:
  - "unsure whether to run make format or make prettier"
  - "encountering CI formatting failures"
  - "working with multiple file types in a PR"
  - "setting up CI iteration workflow"
tripwires:
  - action: "running only prettier after editing Python files"
    warning: "Prettier silently skips Python files. Always use 'make format' for .py files."
---

# Formatting Workflow Decision Tree

Erk uses two formatters: **ruff** (Python) and **prettier** (Markdown). Each tool is file-type-specific and silently ignores files it doesn't handle. This creates a trap where running the wrong formatter appears to succeed but does nothing.

## The Core Problem

**Prettier silently skips Python files.** When you run `make prettier` after editing `.py` files, the command succeeds with exit code 0 but performs no formatting. CI then fails because `ruff format --check` detects the unformatted Python code.

This is the most common formatting failure pattern: an agent edits Python code, runs `make prettier` (the wrong formatter), sees success, and commits. CI immediately fails on the format check.

## Why This Trap Exists

The tools are mutually exclusive by design:

- `ruff format` only processes `.py` files
- `prettier --write '**/*.md'` only processes `.md` files (explicit glob pattern in Makefile:3-4)

Neither tool reports "skipped files" — they just process what matches their pattern and exit successfully. An agent can't tell from the exit code whether formatting actually ran.

## Decision Heuristic

**Did you edit Python files?** → `make format`

**Did you edit Markdown files?** → `make prettier`

**Did you edit both or unsure?** → Run both (they're fast and idempotent)

When in doubt, run both. The cost is negligible compared to a CI failure.

## Standard Iteration Pattern

<!-- Source: Makefile, format and prettier targets -->
<!-- Source: .github/workflows/ci.yml, format and prettier-check jobs -->

The CI workflow runs both format-check and prettier-check in parallel (see .github/workflows/ci.yml format and prettier jobs). To match this locally:

1. **Edit files** (Edit tool or direct writes)
2. **Format Python**: `make format` if you touched `.py` files
3. **Format Markdown**: `make prettier` if you touched `.md` files
4. **Verify**: Run tests, type checks as needed
5. **Commit**

The formatting step MUST happen before commit. Running formatters after pushing means CI will fail and you'll need an additional commit to fix formatting.

## Why Not Auto-Format in Tools?

The Edit tool deliberately preserves literal content without auto-formatting (see [Edit Tool Formatting](edit-tool-formatting.md) for the full rationale). This gives agents precise control but creates the workflow requirement: you must explicitly invoke formatters as a separate step.

The alternative (auto-formatting on every edit) would introduce ambiguity about whether the tool modified your intended output. The trade-off is explicit formatting commands.

## Integration Points

- **Edit tool behavior**: [Edit Tool Formatting](edit-tool-formatting.md) explains why Edit doesn't auto-format
- **CI enforcement**: Both `fast-ci` and `all-ci` targets in Makefile run format-check and prettier-check
- **Make targets**: See Makefile:3-14 for formatter command definitions

## Related Documentation

- [Edit Tool Formatting](edit-tool-formatting.md) - Why Edit tool requires manual formatting
- [CI Tripwires](tripwires.md) - All CI-related tripwires
