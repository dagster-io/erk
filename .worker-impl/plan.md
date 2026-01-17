# Plan: Add Formatter Selection Guidance

## Problem

In a previous session, `prettier` was incorrectly called on Python files (`.py`). Prettier is a JavaScript/TypeScript/CSS/HTML/Markdown formatter - it cannot parse Python files. Python files must use `ruff format`.

The error demonstrated:
```
[error] No parser could be inferred for file ".../activation.py".
```

## Root Cause

No explicit guidance exists about which formatter handles which file types. The Makefile separates formatters implicitly:
- `make format` → `ruff format` (Python)
- `make prettier` → `prettier --write '**/*.md'` (Markdown only)

But this knowledge isn't documented in a discoverable location.

## Solution

Two-pronged approach:
1. **Top-down guidance**: Create a dedicated doc explaining the formatter landscape
2. **Safety net**: Add a tripwire to catch mistakes at execution time

## Implementation

### 1. Create New Doc: `docs/learned/ci/formatter-tools.md`

New file with:
- Clear table mapping file types to formatters
- Explanation of the two formatters in this project
- Makefile targets for formatting
- Common mistake patterns to avoid

Content:
```markdown
---
title: Formatter Tools
read_when:
  - "formatting code"
  - "choosing a formatter"
  - "fixing format errors"
tripwires:
  - action: "running prettier on Python files"
    warning: "Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project."
---

# Formatter Tools

This project uses two formatters, each handling specific file types.

## Formatter Matrix

| File Type | Formatter | Direct Command | Make Target |
|-----------|-----------|----------------|-------------|
| Python (*.py) | ruff | `uv run ruff format <file>` | `make format` |
| Markdown (*.md) | prettier | `npx prettier --write <file>` | `make prettier` |

## Key Rules

1. **Python files → ruff format** (NEVER prettier)
2. **Markdown files → prettier** (NEVER ruff)
3. **When unsure** → use the Make targets which apply correct formatters automatically

## Common Mistakes

### ❌ Wrong: Using prettier on Python
```bash
npx prettier --write src/foo.py  # ERROR: No parser for .py
```

### ✅ Correct: Use ruff for Python
```bash
uv run ruff format src/foo.py
# Or simply:
make format
```

## CI Check Targets

- `make format-check` - Check Python formatting (ruff)
- `make prettier-check` - Check Markdown formatting (prettier)
- `make fast-ci` - Runs both checks (among others)
```

### 2. Update `docs/learned/index.md`

Add entry for the new doc in the CI category.

### 3. Run `erk docs sync`

Regenerate tripwires.md with the new tripwire.

## Files to Modify

1. **Create**: `docs/learned/ci/formatter-tools.md`
2. **Edit**: `docs/learned/index.md` (add entry)
3. **Regenerate**: `docs/learned/tripwires.md` (via `erk docs sync`)

## Verification

1. Run `make fast-ci` to ensure docs pass validation
2. Confirm the new tripwire appears in `docs/learned/tripwires.md`
3. Confirm new doc appears in index