---
title: Prettier Formatting for Claude Commands
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
tripwires:
  - action: "creating .claude/ markdown commands without running Prettier"
    warning: "Run 'make prettier' before committing. CI will fail on un-formatted markdown."
read_when:
  - "Creating slash commands in .claude/commands/"
  - "Modifying existing .claude/ markdown files"
  - "Getting Prettier formatting errors in CI"
---

# Prettier Formatting for Claude Commands

## The Rule

**ALWAYS run `make prettier` after creating or modifying any `.claude/` markdown file.** CI runs `make prettier-check` and will fail on un-formatted files.

## Scope

Prettier **ONLY** formats markdown (`.md` files). It does NOT format:

- **Python code** (`.py`) - Use `ruff format` or `make format`
- **YAML** (`.yml`, `.yaml`) - No formatter in erk
- **JSON** (`.json`) - No formatter in erk

## Troubleshooting

### Prettier Fails on Valid Markdown

Prettier is stricter than markdown parsers about formatting. Run `make prettier` to see what Prettier expects, then adjust.

### Infinite Loop (Format Changes on Every Run)

Rare Prettier bug with certain markdown patterns (e.g., nested lists with code blocks). Simplify the markdown structure to avoid the problematic pattern.

## Related Documentation

- [Slash Command Development](../cli/slash-command-exec-migration.md) - How to write slash commands
