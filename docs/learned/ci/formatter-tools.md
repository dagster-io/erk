---
title: Formatter Tools
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - formatting code
  - choosing a formatter
  - fixing format errors
tripwires:
  - action: "running prettier on Python files"
    warning: "Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project."
  - action: "running prettier programmatically on content containing underscore emphasis"
    warning: "Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output."
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

## Transient Artifact Detection

Prettier failures on `.erk/impl-context/` markdown files serve as cleanup detection:

### The Pattern

When `.erk/impl-context/` isn't properly cleaned up:

1. Prettier runs during CI
2. Prettier finds unformatted markdown in `.erk/impl-context/*.md`
3. CI fails with formatting errors

### Interpreting the Failure

| Files in Error               | Meaning                                   |
| ---------------------------- | ----------------------------------------- |
| `.erk/impl-context/plan.md`  | Remote implementation didn't clean up     |
| `.erk/impl-context/ref.json` | Same - cleanup step failed or was skipped |

### Recovery

```bash
# Clean up the transient artifacts
git rm -rf .erk/impl-context/
git commit -m "Remove .erk/impl-context/ after implementation"
git push
```

### Root Cause

See [erk-impl Workflow Patterns](erk-impl-workflow-patterns.md) for why `.erk/impl-context/` cleanup fails (usually: staged deletion discarded by `git reset --hard`).
