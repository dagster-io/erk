---
title: Prettier Formatting for Claude Commands
tripwires:
  - action: "creating .claude/ markdown commands without running Prettier"
    warning: "Run 'make prettier' before committing. CI will fail on un-formatted markdown."
read_when:
  - "Creating slash commands in .claude/commands/"
  - "Modifying existing .claude/ markdown files"
  - "Getting Prettier formatting errors in CI"
---

# Prettier Formatting for Claude Commands

## Overview

All markdown files in `.claude/` (commands, skills, agents, hooks) must be formatted with Prettier before committing. This ensures consistent formatting and prevents CI failures.

## The Rule

**ALWAYS run Prettier after creating or modifying any `.claude/` markdown file.**

```bash
make prettier
```

## Why This Matters

### CI Will Fail Without Formatting

The CI pipeline runs `make prettier-check` which verifies all markdown files are properly formatted. If you commit un-formatted files:

1. **CI check fails** - The PR cannot be merged
2. **Wasted time** - Another commit needed just for formatting
3. **Noisy diffs** - Formatting changes obscure actual changes

### Prettier Changes Are Mechanical

Prettier enforces:

- **Line length** - Wraps long lines at 120 characters
- **List formatting** - Consistent spacing in bulleted/numbered lists
- **Link formatting** - Standardizes markdown link syntax
- **Heading spacing** - Consistent blank lines around headings
- **Code block formatting** - Proper fencing and language tags

## Workflow

### Creating a New Command

```bash
# 1. Write the command
vim .claude/commands/local/my-command.md

# 2. Run Prettier (REQUIRED before commit)
make prettier

# 3. Review changes
git diff .claude/commands/local/my-command.md

# 4. Commit
git add .claude/commands/local/my-command.md
git commit -m "Add /local:my-command"
```

### Editing an Existing Command

```bash
# 1. Make changes
vim .claude/commands/local/existing-command.md

# 2. Run Prettier (REQUIRED)
make prettier

# 3. Commit
git add .claude/commands/local/existing-command.md
git commit -m "Update /local:existing-command examples"
```

## Common Prettier Changes

### Before (Un-formatted)

```markdown
# My Command

This is a very long line that exceeds the 120 character limit and will be wrapped by Prettier to fit within the configured line length maximum.

- Item 1
- Item 2 (inconsistent spacing)
- Item 3

Examples:

- Example 1
- Example 2
```

### After (Prettier-formatted)

```markdown
# My Command

This is a very long line that exceeds the 120 character limit and will be wrapped by Prettier to fit within the
configured line length maximum.

- Item 1
- Item 2 (inconsistent spacing)
- Item 3

Examples:

- Example 1
- Example 2
```

**Changes:**

1. Added blank line after heading
2. Wrapped long line
3. Standardized list marker spacing (`-` instead of `*`, consistent indentation)

## Verification

### Local Check

```bash
# Check if files are formatted correctly
make prettier-check

# Output when files need formatting:
# Checking Prettier formatting...
# .claude/commands/local/my-command.md
# [error] Code style issues found. Run 'make prettier' to fix.
```

### Fix Formatting

```bash
make prettier

# Output:
# Formatting markdown files with Prettier...
# .claude/commands/local/my-command.md 120ms
# ✨  Done in 0.5s
```

## Integration with devrun Agent

When working with agents that modify `.claude/` files, always run Prettier after the agent completes:

```bash
# Agent modifies a command file
# (agent work happens here)

# REQUIRED: Format before committing
make prettier
git add .claude/commands/
git commit -m "Update command based on agent suggestions"
```

## What Prettier Does NOT Do

Prettier **ONLY** formats markdown (`.md` files). It does NOT format:

- **Python code** (`.py`) - Use `ruff format` or `make format`
- **YAML** (`.yml`, `.yaml`) - No formatter in erk
- **JSON** (`.json`) - No formatter in erk

## Troubleshooting

### Prettier Fails on Valid Markdown

**Problem:** Prettier rejects syntactically valid markdown.

**Cause:** Prettier is stricter than markdown parsers about formatting.

**Fix:** Run `make prettier` to see what Prettier expects, then adjust your markdown to match.

### Infinite Loop (Format Changes on Every Run)

**Problem:** Running `make prettier` changes the file, but running it again changes it back.

**Cause:** Rare Prettier bug with certain markdown patterns (e.g., nested lists with code blocks).

**Fix:** Simplify the markdown structure or rearrange content to avoid the problematic pattern.

## Related Documentation

- [Formatter Tools](formatter-tools.md) - Complete guide to formatters in erk
- [Slash Command Development](../cli/slash-command-exec-migration.md) - How to write slash commands
- [CI Iteration Pattern](ci-iteration.md) - Running CI checks locally
