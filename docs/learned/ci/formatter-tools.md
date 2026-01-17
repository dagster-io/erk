---
title: Formatter Tools
read_when:
  - formatting code
  - choosing a formatter
  - fixing format errors
tripwires:
  - action: "running prettier on Python files"
    warning: "Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project."
---

# Formatter Tools

This project uses two formatters, each handling specific file types.

## Formatter Matrix

| File Type        | Formatter | Direct Command                | Make Target     |
| ---------------- | --------- | ----------------------------- | --------------- |
| Python (\*.py)   | ruff      | `uv run ruff format <file>`   | `make format`   |
| Markdown (\*.md) | prettier  | `npx prettier --write <file>` | `make prettier` |

## Key Rules

1. **Python files -> ruff format** (NEVER prettier)
2. **Markdown files -> prettier** (NEVER ruff)
3. **When unsure** -> use the Make targets which apply correct formatters automatically

## Common Mistakes

### Wrong: Using prettier on Python

```bash
npx prettier --write src/foo.py  # ERROR: No parser for .py
```

### Correct: Use ruff for Python

```bash
uv run ruff format src/foo.py
# Or simply:
make format
```

## CI Check Targets

- `make format-check` - Check Python formatting (ruff)
- `make prettier-check` - Check Markdown formatting (prettier)
- `make fast-ci` - Runs both checks (among others)
