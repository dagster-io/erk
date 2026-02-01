---
title: Formatting Workflow Decision Tree
read_when:
  - "unsure whether to run make format or make prettier"
  - "encountering CI formatting failures"
  - "working with multiple file types in a PR"
  - "setting up CI iteration workflow"
---

# Formatting Workflow Decision Tree

Erk uses two formatters: **ruff** for Python and **prettier** for Markdown. This guide shows when to use each.

## Quick Reference

| File Type        | Command          | Tool     |
| ---------------- | ---------------- | -------- |
| `.py`            | `make format`    | ruff     |
| `.md`            | `make prettier`  | prettier |
| Mixed or unclear | Both (see below) | both     |

## Decision Tree

```
Did you edit Python files (.py)?
├─ YES → Run `make format`
│
├─ NO → Did you edit Markdown files (.md)?
│   ├─ YES → Run `make prettier`
│   └─ NO → Skip formatting
│
└─ UNCLEAR or BOTH → Run both:
    1. make format
    2. make prettier
```

## The Prettier Trap

**CRITICAL**: Prettier silently does nothing on Python files.

```bash
# This looks like it works, but does nothing for .py files
make prettier  # ❌ Silently skips Python files

# Always use ruff for Python
make format    # ✅ Actually formats Python files
```

If you run only `make prettier` after editing Python code, CI will fail because ruff wasn't run.

## Standard CI Iteration Sequence

When iterating on code until CI passes:

1. **Make your edits** (using Edit tool or direct file writes)
2. **Format Python**: `make format` (if you edited `.py` files)
3. **Format Markdown**: `make prettier` (if you edited `.md` files)
4. **Run tests**: `pytest` or `make test`
5. **Type check**: `make ty`
6. **Commit and push**
7. **Check CI**: If it fails, repeat from step 1

## When to Run Both

Run both formatters if:

- You edited both `.py` and `.md` files
- You're unsure what you edited
- You want to be safe (both commands are fast)

```bash
# Safe pattern: format everything
make format
make prettier
```

## Format Before Commit

**Best practice**: Always run formatting before committing:

```bash
# Before git commit
make format
make prettier
git add -u
git commit -m "Your message"
```

This prevents CI formatting failures.

## Integration with Edit Tool

The Claude Code Edit tool preserves exact indentation without auto-formatting. See [Edit Tool Formatting](edit-tool-formatting.md) for details on why you must run `make format` after editing Python files with multiline strings.

## Related Documentation

- [Edit Tool Formatting](edit-tool-formatting.md) - Why Edit tool requires manual formatting
- [CI Tripwires](tripwires.md) - All CI-related tripwires
